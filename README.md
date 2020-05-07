# Encapsia API Library

![Tests](https://github.com/tcorbettclark/encapsia-api/workflows/Tests/badge.svg)

REST API for working with Encapsia.

See <https://www.encapsia.com.>

## Release checklist

* Run: `black .`
* Run: `isort`
* Run: `flake8 .`
* Run: `nose2 -v`
* Ensure `git tag`, package version (via `poetry version`), and `encapsia_api.__version__` are all equal.
