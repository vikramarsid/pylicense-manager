========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis|
        |
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/pylicense-manager/badge/?style=flat
    :target: https://readthedocs.org/projects/pylicense-manager
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/vikramarsid/pylicense-manager.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/vikramarsid/pylicense-manager

.. |version| image:: https://img.shields.io/pypi/v/pylicense-manager.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/pylicense-manager

.. |commits-since| image:: https://img.shields.io/github/commits-since/vikramarsid/pylicense-manager/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/vikramarsid/pylicense-manager/compare/v0.1.0...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/pylicense-manager.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/pylicense-manager

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/pylicense-manager.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/pylicense-manager

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/pylicense-manager.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/pylicense-manager


.. end-badges

Python PYPI packages license manager

* Free software: MIT license

Installation
============

::

    pip install pylicense-manager

Documentation
=============

https://pylicense-manager.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
