from setuptools import setup, find_packages
from codecs import open
import os
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.in') as f:
    install_reqs = f.readlines()


def prerelease_local_scheme(version):
    """Return local scheme version unless building on master in CircleCI.
    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """

    from setuptools_scm.version import get_local_node_and_date

    if 'CIRCLE_BRANCH' in os.environ and \
       os.environ.get('CIRCLE_BRANCH') == 'master':
        return ''
    else:
        return get_local_node_and_date(version)


setup(
    name='girder-jupyter',
    use_scm_version={'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools_scm'],
    description='A jupyter content manager for Girder',
    long_description=long_description,
    url='https://github.com/girder/girder_jupyter',
    author='Kitware Inc',
    author_email='kitware@kitware.com',
    license='BSD 3-Clause',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Jupyter',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='jupyter girder data management',

    packages=find_packages(),

    install_requires=install_reqs,

    extras_require={

    }
)
