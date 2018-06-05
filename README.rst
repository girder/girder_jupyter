==============
girder_jupyter
==============
|build-status| |pypi-version| |pypi-status|

The Jupyter Notebook web application provides a graphical interface for creating, opening, renaming, and deleting files in a virtual filesystem. `girder_jupyter <https://github.com/girder/girder_jupyter>`__ is a python package that implements a `contents manager <http://jupyter-notebook.readthedocs.io/en/latest/extending/contents.html>`_
to allow Girder to become a backend for this virtual filesystem. This allows notebooks and files to be stored
in a Girder server from within Jupyter.

Getting Started
===============

Install the package in the Python environment you are running your Jupyter server in:

.. code-block:: bash

    pip install girder-jupyter


Add the following options to your :code:`jupyter_notebook_config.py`

.. code-block:: python

    c.NotebookApp.contents_manager_class = 'girder_jupyter.contents.manager.GirderContentsManager'
    c.GirderContentsManager.api_key = '<api key>'
    c.GirderContentsManager.api_url = '<api url>'

Where :code:`<api key>` is replaced with a `Girder API key <https://girder.readthedocs.io/en/latest/user-guide.html?highlight=API%20Key#api-keys>`__ for the Girder server and :code:`<api url>` is the URL to Girder instance you want
to use for example http://localhost:8080/api/v1.

Configuration Parameters
========================

- :code:`api_url` - An API URL for the Girder server. Defaults to 'http://localhost:8080/api/v1'
- :code:`api_key` -A `Girder API key <https://girder.readthedocs.io/en/latest/user-guide.html?highlight=API%20Key#api-keys>`__ key for the Girder server at :code:`api_url`. The key should have read and write permission scope.
- :code:`token` - A Girder token for the Girder server at :code:`api_url`. This parameter is particularly useful when running instances from JupyterHub.
- :code:`root` - The root in the Girder hierarchy to use as the content managers root. This path can include :code:`{login}` which will be replace with the current users login. Defaults to :code:`'user/{login}'`

Note that either :code:`api_key` or :code:`token` must be provided for the contents manager to be able to
authenticate with the Girder server.

.. |build-status| image:: https://circleci.com/gh/girder/girder_jupyter.png?style=shield
    :target: https://circleci.com/gh/girder/girder_jupyter
    :alt: Build Status

.. |pypi-version| image:: https://img.shields.io/pypi/v/girder-jupyter.svg
    :target: https://pypi.python.org/pypi/girder-jupyter/
    :alt: PyPI version

.. |pypi-status| image:: https://img.shields.io/pypi/status/girder-jupyter.svg
    :target: https://pypi.python.org/pypi/girder-jupyter/
    :alt: PyPI status

