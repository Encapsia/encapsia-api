# Encapsia API Library

REST API for working with Encapsia.

See <https://www.encapsia.com.>

## Release checklist

* Run: `black .`
* Run: `isort`
* Run: `flake8 .`
* Run: `nose2 -v`
* Ensure `git tag`, package version (via `poetry version`), and `enacpsia_api.__version__` are all equal.
