from notebook.services.contents.tests.test_contents_api import  API, APITest, Config
from nbformat.v4 import (
    new_notebook, new_markdown_cell,
)
from functools import partial
import girder_client
from six import BytesIO
import os
import json


from .constants import GIRDER_API_KEY, GIRDER_API_URL

class GirderContentsTest(APITest):
    gc = girder_client.GirderClient(apiUrl=GIRDER_API_URL)

    def _get_girder_path(self, path):
        return ('/user/%s/Private/%s' % (self.user['login'],
                path.lstrip('/') ) ).rstrip('/')

    @classmethod
    def setup_class(cls):
        cls.config = Config()
        cls.config.NotebookApp.contents_manager_class = 'girder_jupyter.contents.girderfilemanager.GirderFileManager'
        cls.config.GirderFileManager.api_key = GIRDER_API_KEY
        cls.config.GirderFileManager.root = 'user/{login}/Private'
        cls.gc.authenticate(apiKey=GIRDER_API_KEY)
        cls.user = cls.gc.get("user/me")
        super(APITest, cls).setup_class()


    def delete_dir(self, path):
        path = self._get_girder_path(path)
        resource = self._resource(path)
        self.gc.delete("folder/{}".format(resource['_id']))

    def delete_file(self, path):
        path = self._get_girder_path(path)
        resource = self._resource(path)
        self.gc.delete("item/{}".format(resource['_id']))

    # def setUp(self):
    #     for d in (self.dirs + self.hidden_dirs):
    #         self.make_dir(d)
    #         self.addCleanup(partial(self.delete_dir, d))

    #     for d, name in self.dirs_nbs:
    #         # create a notebook
    #         nb = new_notebook()
    #         nbname = u'{}/{}.ipynb'.format(d, name)
    #         self.make_nb(nbname, nb)
    #         self.addCleanup(partial(self.delete_file, nbname))

    #         # create a text file
    #         txt = self._txt_for_name(name)
    #         txtname = u'{}/{}.txt'.format(d, name)
    #         self.make_txt(txtname, txt)
    #         self.addCleanup(partial(self.delete_file, txtname))

    #         blob = self._blob_for_name(name)
    #         blobname = u'{}/{}.blob'.format(d, name)
    #         self.make_blob(blobname, blob)
    #         self.addCleanup(partial(self.delete_file, blobname))
    #     self.api = API(self.request)



    def test_mkdir(self):
        path = u'foo/bar/baz/biz/buz/lol/lal'
        resp = self.api.mkdir(path)
        self._check_created(resp, path, type='directory')

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

        return self.gc.resourceLookup(path, test=True)


    def make_root_dir(self, name):
        return self.gc.createFolder(self.user["_id"], name, parentType="user")

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
        elif  parent['_modelType'] not in ['user', 'folder']:
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
        folder = self.gc.createFolder(parent['_id'],
                            os.path.basename(path),
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
        # os_path = self.to_os_path(api_path)


        # with io.open(os_path, 'w', encoding='utf-8') as f:
        #     write(nb, f, version=4)

    # def test_make_txttt(self)
