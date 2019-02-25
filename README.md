# Encapsia API Library

REST API for working with Encapsia.

See https://www.encapsia.com.

# Release checklist

* Run: flake8 --ignore=E501 .
* Run: black .
* Run: isort --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width=88 -y
* Ensure git tag, package version, and enacpsia_api.__version__ are all equal.