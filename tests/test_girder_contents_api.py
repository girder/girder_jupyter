from notebook.services.contents.tests.test_contents_api import APITest, Config

import girder_client
from six import BytesIO
import os
import json


from .constants import GIRDER_API_URL


class GirderContentsTest(APITest):
    gc = girder_client.GirderClient(apiUrl=GIRDER_API_URL)

    def _get_girder_path(self, path):
        return ('/user/%s/Private/%s' % (self.user['login'],
                path.lstrip('/'))).rstrip('/')

    @classmethod
    def setup_class(cls):
        cls.config = Config()
        cls.config.NotebookApp.ip = '127.0.0.1'
        cls.config.NotebookApp.contents_manager_class =\
            'girder_jupyter.contents.manager.GirderContentsManager'

        if 'GIRDER_API_KEY' in os.environ:
            api_key = os.environ['GIRDER_API_KEY']
            cls.config.GirderContentsManager.api_key = api_key
            cls.gc.authenticate(apiKey=api_key)
        elif 'GIRDER_USER' in os.environ and 'GIRDER_PASSWORD' in os.environ:
            user = os.environ['GIRDER_USER']
            password = os.environ['GIRDER_PASSWORD']
            cls.gc.authenticate(user, password)
            cls.config.GirderContentsManager.token = cls.gc.token
        else:
            raise Exception('No Girder credentials configured.')

        cls.config.GirderContentsManager.root = 'user/{login}/Private'
        cls.user = cls.gc.get('user/me')
        super(APITest, cls).setup_class()

    def delete_dir(self, path):
        path = self._get_girder_path(path)
        resource = self._resource(path)
        if resource is not None:
            self.gc.delete('folder/{}'.format(resource['_id']))

    def delete_file(self, path):
        path = self._get_girder_path(path)
        resource = self._resource(path)
        if resource is not None:
            self.gc.delete('item/{}'.format(resource['_id']))

    def isdir(self, path):
        path = self._get_girder_path(path)
        resource = self._resource(path)
        return self._is_type(resource, model_type=['folder', 'item'])

    def isfile(self, path):
        path = self._get_girder_path(path)
        resource = self._resource(path)
        if self._is_type(resource, model_type=['item']):
            resource = self._resource(os.path.join(path, os.path.basename(path)))
            return self._is_type(resource, model_type=['file'])
        return False

    def _is_type(self, resource, model_type):
        if resource is None:
            return False
        if not isinstance(model_type, list):
            model_type = list(model_type)
        return resource['_modelType'] in model_type

    def _resource(self, path):
        try:
            return self.gc.resourceLookup(path)
        except girder_client.HttpError:
            return None

    def make_root_dir(self, name):
        return self.gc.createFolder(self.user['_id'], name, parentType='user')

    def _get_or_create_folder_parent(self, path):
        """
        Get the parent directory of a specific path.
        If needed, create all the required intermediate folders.
        """
        parent_path = os.path.dirname(path.lstrip('/').rstrip('/'))
        parent = self._resource(self._get_girder_path(parent_path))
        if parent is None:
            grandpa = self._get_or_create_folder_parent(parent_path)
            parent = self.gc.createFolder(grandpa['_id'],
                                          os.path.basename(parent_path),
                                          parentType=grandpa['_modelType'])
        elif parent['_modelType'] not in ['user', 'folder']:
            self.fail('Permission denied: %s' % parent_path)

        return parent

    def _get_or_create_file_parent(self, path):
        # an item is an acceptable parent type only for a file
        # and only at the first iteration
        parent_path, name = os.path.split(path.lstrip('/').rstrip('/'))
        resource = self._resource(self._get_girder_path(path))
        if resource is None:
            grandpa = self._get_or_create_dir(parent_path)
            parent = self.gc.createItem(grandpa['_id'], name)
            return parent
        elif resource['_modelType'] == 'item':
            return resource
        elif resource['_modelType'] == 'file':
            self.fail('Only an item can contain a file')
        elif resource['_modelType'] == 'folder':
            self.fail('Only an item can contain a file')

    def make_dir(self, path):
        """
        Create all necessary folder for a given path.
        """
        parent = self._get_or_create_folder_parent(path)
        folder = self.gc.createFolder(parent['_id'],  os.path.basename(path),
                                      parentType=parent['_modelType'])
        return folder

    def _get_or_create_dir(self, path):
        resource = self._resource(self._get_girder_path(path))
        if resource is None:
            return self.make_dir(path)
        elif resource['_modelType'] != 'folder':
            self.fail('The requested resource is not a folder %s' % path)
        else:
            return resource

    def make_txt(self, path, content):
        parent = self._get_or_create_file_parent(path)
        content = content.encode('utf8')
        size = len(content)
        stream = BytesIO(content)
        self.gc.uploadFile(parent['_id'], stream, os.path.basename(path), size)

    def make_blob(self, path, content):
        parent = self._get_or_create_file_parent(path)
        # content = content.encode('utf8')
        size = len(content)
        stream = BytesIO(content)
        self.gc.uploadFile(parent['_id'], stream, os.path.basename(path), size)

    def make_nb(self, path, nb):
        """Make a notebook file at a given api_path"""
        content = json.dumps(nb, indent=2)
        self.make_txt(path, content)
