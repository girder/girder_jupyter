from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='girder_jupyter',

    version='0.0.1',

    description='A jupyter content manager for Girder',
    long_description=long_description,

    url='https://github.com/cjh1/girder_jupyter',

    author='Kitware Inc',
    author_email='chris.harris@kitware.com',

    license='BSD 3-Clause',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Girder/Jupyter Developers',
        'Topic :: Software Development :: Data management',

        'License :: OSI Approved :: BSD 3-Clause',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='jupyter girder data management',

    packages=['girder_jupyter', 'girder_jupyter.contents'],

    install_requires=[
        'girder_client',
        'python-dateutil',
        'nbformat',
        'notebook',
        'traitlets',
        'tornado',
        'six'
    ],

    extras_require={

    }
)
