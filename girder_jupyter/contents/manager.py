import os
from six import BytesIO
import dateutil
import base64
import nbformat


from notebook.services.contents.manager import ContentsManager
from notebook.services.contents.filecheckpoints import GenericFileCheckpoints

from traitlets import default, Unicode, Instance

from tornado import web

import girder_client


class GirderContentsManager(ContentsManager):

    api_url = Unicode(
        allow_none=True,
        config=True,
        help='A Girder API url.',
        default_value='http://localhost:8080/api/v1'
    )

    api_key = Unicode(
        allow_none=True,
        config=True,
        help='A Girder API key.',
        default_value=None
    )

    token = Unicode(
        allow_none=True,
        config=True,
        help='A Girder token.'
    )

    gc = Instance(girder_client.GirderClient)

    root = Unicode(
        allow_none=True,
        config=True,
        help='The root in the Girder hierarchy, defaults to user/<login>.'
        'This path can include {login} which will be replace with the current users login.',
        default_value='user/{login}'
    )

    @default('gc')
    def _gc(self):
        gc = girder_client.GirderClient(apiUrl=self.api_url)
        if self.api_key is not None:
            gc = girder_client.GirderClient(apiUrl=self.api_url)
            gc.authenticate(apiKey=self.api_key)
        elif self.token is not None:
            gc.token = self.token

        return gc

    @default('checkpoints_class')
    def _checkpoints_class(self):

        return GenericFileCheckpoints

    @default('checkpoints_kwargs')
    def _checkpoints_kwargs(self):
        home = os.path.expanduser('~')

        return {
            'root_dir': os.path.join(home, '.ipynb_checkpoints')
        }

    def _render_login(self, root):
        if '{login}' in self.root:
            me = self.gc.get('user/me')
            # Replace {login} with users login.
            try:
                root = root.format(login=me['login'])
            except KeyError:
                pass

        return root

    def __init__(self, *args, **kwargs):
        super(GirderContentsManager, self).__init__(*args, **kwargs)
        # Render {login}
        self.root = self._render_login(self.root)

    def _resource(self, path):
        try:
            return self.gc.resourceLookup(path)
        except girder_client.HttpError:
            return None

    def _resource_exists(self, path, model_type):
        resource = self._resource(path)

        return self._is_type(resource, model_type)

    def _is_type(self, resource, model_types):
        if resource is None:
            return False

        if not isinstance(model_types, list):
            model_types = [model_types]

        return resource['_modelType'] in model_types

    def _is_folder(self, resource):
        return self._is_type(resource, 'folder')

    def _is_item(self, resource):
        return self._is_type(resource, 'item')

    def _is_user(self, resource):
        return self._is_type(resource, 'user')

    def _is_file(self, resource):
        return self._is_type(resource, 'file')

    def _file(self, path):
        resource = self._resource(path)

        name = path.split('/')[-1]

        if self._is_item(resource):
            return self._file_by_name(resource['_id'], name)

        return None

    def _file_by_name(self, item_id, name):
        for file in self.gc.listFile(item_id):
            if file['name'] == name:
                return file

        return None

    def _list_resource(self, resource):
        listing = []

        if self._is_folder(resource):
            params = {
                'folderId': resource['_id']
            }

            listing += self.gc.get('item', params)

        params = {
            'parentId': resource['_id'],
            'parentType': resource['_modelType']
        }

        listing += self.gc.get('folder', params)

        return listing

    def _get_girder_path(self, path):

        return ('%s/%s' % (self.root, path)).rstrip('/')

    def dir_exists(self, path):
        """Does a directory exist at the given path?
        Like os.path.isdir

        Parameters
        ----------
        path : string
            The path to check
        Returns
        -------
        exists : bool
            Whether the path does indeed exist.

        """

        path = path.strip('/')
        girder_path = self._get_girder_path(path)

        return self._resource_exists(girder_path, ['folder', 'item', 'user'])

    def is_hidden(self, path):
        """Is path a hidden directory or file?
        Parameters
        ----------
        path : string
            The path to check. This is an API path (`/` separated,
            relative to root dir).
        Returns
        -------
        hidden : bool
            Whether the path is hidden.

        """

        return False

    def file_exists(self, path=''):
        """Does a file exist at the given path?
        Like os.path.isfile

        Parameters
        ----------
        path : string
            The API path of a file to check for.
        Returns
        -------
        exists : bool
            Whether the file exists.

        """
        path = path.strip('/')
        girder_path = self._get_girder_path(path)

        return self._file(girder_path) is not None

    def _has_write_access(self, resource):
        if self._is_folder(resource) or self._is_user(resource):
            return resource['_accessLevel'] > 0
        elif self._is_item(resource):
            # Get the containing folder to check access
            folder = self.gc.getFolder(resource['folderId'])
            return self._has_write_access(folder)
        elif self._is_file(resource):
            # Get the containing item to check access
            folder = self.gc.getItem(resource['itemId'])
            return self._has_write_access(folder)
        else:
            # TODO Need to work out error reporting
            raise Exception('Unexpected resource type: %s' % resource['_modelType'])

    def _base_model(self, path, resource):
        """Build the common base of a contents model
        Parameters
        ----------
        path : string
            The path to the resource
        resource : dict
            The Girder file or folder model
        """

        created = resource['created']
        updated = resource.get('updated', created)

        # Create the base model.
        model = {}
        model['name'] = resource.get('name', resource.get('login'))
        model['path'] = path
        model['last_modified'] = dateutil.parser.parse(updated)
        model['created'] = dateutil.parser.parse(created)
        model['content'] = None
        model['format'] = None
        model['mimetype'] = None
        model['writable'] = self._has_write_access(resource)

        return model

    def _dir_model(self, path, resource, content=True, format=None):
        """Build a model for a directory
        if content is requested, will include a listing of the directory
        """
        model = self._base_model(path, resource)
        model['type'] = 'directory'
        if content:
            model['content'] = contents = []
            for resource in self._list_resource(resource):
                name = resource['name']
                if self.should_list(name) and not name.startswith('.'):
                    contents.append(self._get(
                        '%s/%s' % (path, name), resource,
                        content=False, format=format)
                    )

            model['format'] = 'json'

        return model

    def _file_model(self, path, file, content=True, format=None):
        """Build a model for a file
        if content is requested, include the file contents.
        format:
          If 'text', the contents will be decoded as UTF-8.
          If 'base64', the raw bytes contents will be encoded as base64.
          If not specified, try to decode as UTF-8, and fall back to base64
        """
        girder_path = self._get_girder_path(path)
        model = self._base_model(path, file)
        model['type'] = 'file'
        model['mimetype'] = file['mimeType']

        if content:
            stream = BytesIO()
            self.gc.downloadFile(file['_id'], stream)

            if format == 'text':
                try:
                    content = stream.getvalue().decode('utf8')
                except UnicodeError:
                    if format == 'text':
                        raise web.HTTPError(
                            400, '%s is not UTF-8 encoded' % girder_path,
                            reason='bad format')
            elif format == 'base64':
                content = base64.b64encode(stream.getvalue()).decode('ascii')
            # If not specified, try to decode as UTF-8, and fall back to base64
            else:
                try:
                    content = stream.getvalue().decode('utf8')
                    format = 'text'
                except UnicodeError:
                    content = base64.b64encode(stream.getvalue()).decode('ascii')
                    format = 'base64'

            model.update(
                content=content,
                format=format
            )

        return model

    def _item_model(self, path, item, content=True, format=None):
        name = path.split('/')[-1]
        files = list(self.gc.listFile(item['_id']))
        # We short cut an item just create to contain a file
        item_is_container = False

        for file in files:
            if file['name'] == name:
                item_is_container = len(files) == 1
                item_file = file

        if item_is_container:
            return self._file_model(path, item_file, content, format)

        # Other treat item as read-only directories
        model = self._base_model(path, item)
        model['writable'] = False
        model['type'] = 'directory'
        if content:
            model['content'] = contents = []
            for file in files:
                contents.append(self._get(
                    '%s/%s' % (path, file['name']), file,
                    content=False, format=format)
                )

            model['format'] = 'json'

        return model

    def _notebook_model(self, path, resource, content=True):
        name = path.split('/')[-1]
        # Shortcut item
        if self._is_item(resource):
            resource = self._file_by_name(resource['_id'], name)

        model = self._base_model(path, resource)
        model['type'] = 'notebook'

        if content:
            stream = BytesIO()
            self.gc.downloadFile(resource['_id'], stream)
            nb = nbformat.reads(stream.getvalue().decode('utf8'), as_version=4)
            self.mark_trusted_cells(nb, path)
            model['content'] = nb
            model['format'] = 'json'
            self.validate_notebook_model(model)

        return model

    def _get(self, path, resource, content=True, type=None, format=None):
        """Get a file or directory model."""

        girder_path = self._get_girder_path(path)

        if not self._is_type(resource, ['file', 'item', 'folder', 'user']):
            raise web.HTTPError(404, 'No such file or directory: %s' % girder_path)

        if type == 'notebook' or (type is None and path.endswith('.ipynb')):
            model = self._notebook_model(path, resource, content)
        elif self._is_folder(resource) or self._is_user(resource):
            if type not in (None, 'directory'):
                raise web.HTTPError(
                    400, '%s is a directory, not a %s' % (girder_path, type), reason='bad type')
            model = self._dir_model(path, resource, content, format)
        elif self._is_item(resource):
            if type not in (None, 'file', 'notebook'):
                raise web.HTTPError(
                    400, '%s is a file, not a %s' % (girder_path, type), reason='bad type')
            model = self._item_model(path, resource, content, format)
        else:
            if type == 'directory':
                raise web.HTTPError(
                    400, '%s is not a directory' % girder_path, reason='bad type')
            model = self._file_model(path, resource, content=content, format=format)

        return model

    def get(self, path, content=True, type=None, format=None):
        """Get a file or directory model."""
        path = path.strip('/')
        girder_path = self._get_girder_path(path)

        resource = self._resource(girder_path)

        return self._get(path, resource, content, type, format)

    def _upload_to_path(self, content, mime_type, format, path):
        parts = path.split('/')
        name = parts[-1]
        folder_path = parts[:-1]

        parent = self._create_folders('/'.join(folder_path))

        if self._is_user(parent):
            msg = "The Girder user's home location may only contain " \
                'folders. Create or navigate to another folder before ' \
                'creating or uploading a file.'
            raise web.HTTPError(400, msg, reason=msg)
        elif self._is_item(parent):
            item = parent
        else:
            item = self.gc.loadOrCreateItem(name, parent['_id'], reuseExisting=True)

        file = self._file_by_name(item['_id'], name)

        # Get content in right format
        if format == 'text':
            content = content.encode('utf8')
        else:
            b64_content = content.encode('ascii')
            content = base64.b64decode(b64_content)
        size = len(content)

        stream = BytesIO(content)

        if file is None:
            self.gc.uploadFile(item['_id'], stream, name, size, mimeType=mime_type)
        else:
            self.gc.uploadFileContents(file['_id'], stream, size)

    def _create_folders(self, path):
        """
        Create all necessary folder for a given path.
        """
        parts = path.split('/')
        root = '/'.join(parts[:2])
        path = parts[2:]

        current_resource = self._resource(root)
        if current_resource is None:
            raise web.HTTPError(404, 'No such file or directory: %s' % path)

        for resource_name in path:
            # Can't create folder under an item so return permission denied
            if self._is_item(current_resource):
                raise web.HTTPError(403, 'Permission denied: %s' % resource_name)

            next_resource = next(
                self.gc.listFolder(current_resource['_id'],
                                   name=resource_name,
                                   parentFolderType=current_resource['_modelType']), None)

            # Check for items
            if next_resource is None:
                next_resource = next(self.gc.listItem(current_resource['_id'],
                                                      name=resource_name), None)

            if next_resource is None:
                # Can't create folder under an item so return permission denied
                if self._is_item(current_resource):
                    raise web.HTTPError(403, 'Permission denied: %s' % resource_name)
                current_resource = self.gc.createFolder(current_resource['_id'],
                                                        resource_name,
                                                        parentType=current_resource['_modelType'])
            else:
                current_resource = next_resource

        return current_resource

    def save(self, model, path):
        """
        Save a file or directory model to path.
        Should return the saved model with no content.  Save implementations
        should call self.run_pre_save_hook(model=model, path=path) prior to
        writing any data.
        """
        path = path.strip('/')
        girder_path = self._get_girder_path(path)

        if 'type' not in model:
            raise web.HTTPError(400, 'No file type provided')
        if 'content' not in model and model['type'] != 'directory':
            raise web.HTTPError(400, 'No file content provided')
        for segment in path.split('/'):
            if segment.startswith('.'):
                raise web.HTTPError(400, 'Hidden files and folders are not allowed.')

        try:
            if model['type'] == 'notebook':
                nb = nbformat.from_dict(model['content'])
                self.check_and_sign(nb, path)
                nb = nbformat.writes(nb, version=nbformat.NO_CONVERT)
                self._upload_to_path(nb, 'application/json', 'text', girder_path)
            elif model['type'] == 'file':
                self._upload_to_path(model.get('content'), model.get('mimetype'),
                                     model.get('format'), girder_path)
            elif model['type'] == 'directory':
                self._create_folders(girder_path)
            else:
                raise web.HTTPError(400, 'Unhandled contents type: %s' % model['type'])
        except web.HTTPError:
            raise
        except Exception as e:
            self.log.error('Error while saving file: %s %s', path, e, exc_info=True)
            raise web.HTTPError(500, 'Unexpected error while saving file: %s %s' % (path, e))

        validation_message = None
        if model['type'] == 'notebook':
            self.validate_notebook_model(model)
        validation_message = model.get('message', None)

        model = self.get(path, content=False)
        model['message'] = validation_message

        return model

    def delete_file(self, path, allow_non_empty=False):
        """Delete the file or directory at path."""
        path = path.strip('/')
        girder_path = self._get_girder_path(path)
        resource = self._resource(girder_path)
        if resource is None:
            raise web.HTTPError(404, 'Path does not exist: %s' % girder_path)

        if self._is_folder(resource):
            # Don't delete non-empty directories.
            # TODO A directory containing only leftover checkpoints is
            # considered empty.
            resources = self._list_resource(resource)
            if not allow_non_empty and resources:
                raise web.HTTPError(400, 'Directory %s not empty' % girder_path)

            self.gc.delete('folder/%s' % resource['_id'])
        else:
            name = path.split('/')[-1]
            files = list(self.gc.listFile(resource['_id']))
            deleted = False
            for file in files:
                if file['name'] == name:
                    self.gc.delete('file/%s' % file['_id'])
                    deleted = True

            if not deleted:
                raise web.HTTPError(404, 'File does not exist: %s' % girder_path)

            # If the item only contained that file clean it up?
            # TODO: What about item metadata?
            if len(files):
                self.gc.delete('item/%s' % resource['_id'])

    def rename_file(self, old_path, new_path):
        """
        Rename a file or directory.

        N.B. Note currently we only support renaming, not moving to another folder.
        Its not clear that this operation can be performed using rename, it doesn't
        seem to be exposed through jlab.
        """
        girder_path = self._get_girder_path(old_path)
        resource = self._resource(girder_path)
        if resource is None:
            raise web.HTTPError(404, 'Path does not exist: %s' % girder_path)

        # Check if new_path already exists
        new_girder_path = self._get_girder_path(new_path)
        existing_resource = self._resource(new_girder_path)
        if existing_resource is not None:
            raise web.HTTPError(409, u'File already exists: %s' % new_path)

        def _update_name(type, resource, name):
            params = {
                'name': name
            }
            self.gc.put('%s/%s' % (type, resource['_id']), params)

        name = os.path.basename(new_path)
        if self._is_folder(resource):
            _update_name('folder', resource, name)
        elif self._is_file(resource):
            _update_name('file', resource, name)
        elif self._is_item(resource):
            item_id = resource['_id']
            item = self.gc.getItem(item_id)
            files = list(self.gc.listFile(item_id))
            _update_name('item', resource, name)
            # If we have one file and the names match then rename both.
            # This may or may not be the right behavior.
            if len(files) == 1 and item['name'] == resource['name']:
                _update_name('file', files[0], name)

    def delete(self, path):
        """Delete a file/directory and any associated checkpoints."""
        self.delete_file(path, allow_non_empty=True)

    def rename(self, old_path, new_path):
        """Rename a file and any checkpoints associated with that file."""
        self.rename_file(old_path, new_path)
