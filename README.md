# Encapsia API Library

![Workflows](https://github.com/encapsia/encapsia-api/actions/workflows/main.yml/badge.svg)

[![Known Vulnerabilities](https://snyk.io/test/github/encapsia/encapsia-api/badge.svg?targetFile=requirements.txt)](https://snyk.io/test/github/encapsia/encapsia-api?targetFile=requirements.txt)

REST API for working with Encapsia.

See <https://www.encapsia.com.>

## Release checklist

* Run: `black .`
* Run: `isort .`
* Run: `flake8 .`
* Run: `mypy .`
* Run: `pytest .`
* Run: `poetry export -f requirements.txt >requirements.txt` (for snyk scanning)
* Set package version (via `poetry version`) and `encapsia_api.__version__` to the new version. Commit, then set `git tag`.
