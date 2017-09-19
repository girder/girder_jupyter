girder_jupyter
=========================================================================================

girder_jupyter is a python package that implements a `content manager <http://jupyter-notebook.readthedocs.io/en/latest/extending/contents.html>`_
to allow Girder to become a backend for a Jupyter notebook server.

Configuration
=============

Add the following options to your :code:`jupyter_notebook_config.py` 
::
    c.NotebookApp.contents_manager_class = 'girder_jupyter.contents.girderfilemanager.GirderFileManager'
    c.GirderFileManager.api_key = '<api key>'



   
