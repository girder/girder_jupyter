=============
Release Notes
=============

This is the summary list of changes to girder_jupyter between each release. For full
details, see the commit logs at https://github.com/girder/girder_jupyter

Unreleased
==========

Added Features
--------------

Bug fixes
---------

Changes
-------

Deprecations
------------

DevOps
------

Removals
--------

Security Fixes
--------------


girder_jupyter 0.2.0
====================


Bug fixes
---------

* Guard against file creation under a user.

Changes
-------
* The contents manager class has been renamed to girder_jupyter.contents.manager.GirderContentsManager
to better fit with established naming conventions.

girder_jupyter 0.2.1
====================


Bug fixes
---------

* Improve error message when user tries to create a file under a Girder user.
