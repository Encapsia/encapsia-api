# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.3] - 2023-10-13

### Changed

- Dependency updates

## [0.4.2] - 2023-05-27

### Added

- Support PEP-561 (added `py.typed` to the package).

## [0.4.1] - 2023-05-27

### Changed

- Dependency updates, mainly to address CVE-2023-32681 in python-requests.
- Loosened up requirements specifications by using e.g. `foo>=1.2` rather than
  `foo^1.2` so that clients are less constrained by this library's dependencies.

## [0.4.0] - 2023-05-05

### Added

- Added `logout()` method to delete the current token.
- Added a `login_extend(duration)` method to call `/v1/login/extend/<duration>`. Closes
  #53.
- Build: Added `pre-commit` hooks and added github action to run them.
  
### Changed

- Build: move black, mypy and pytest configs into pyproject.toml, added type stubs for
  libraries.
- Build: remove isort and flake8 and replace with `ruff`.
- Refactor: rename `lib.temp_dir` to `lib.make_temp_dir_path`.
- Changed minimum Python version to 3.8 (stop supporting 3.7 which will be end-of-life
  in June 2023).
- Refactor: use a few python 3.8 features, replacing "manual" solutions.
- Refactor: replace `dict()` and `set()` calls with dict and set literals.
- Refactor: replaced mutable default value of arguments (like `[]` or `{}`).
- Changed `PackageMaker.make_package` to require a `directory` argument (not defaulting
  to `/tmp`).
- Changed `PluginMaker` methods `make_plugin()` and `make_and_upload_plugin()` to use a
  system-default temporary directory instead of hard-coded `/tmp`.

## [0.3.3] - 2022-12-06

### Changed

- Drop the lifespan parameter of `login_transfer()`, since Core does not
  use it (Bug #32)

### Fixed

- `get_config()` raises a `KeyError` regardless of the error encountered, hiding
  networking or authorization errors. Fixes #48.
- Modify pip_install_from_plugin() so that process output is visible in
  Analytics/Jupyter notebooks (Bug #37)


## [0.3.2] - 2022-11-09

### Changed

- Allow sending include_deleted|metadata flags in get_blobs()


## [0.3.1] - 2021-10-19

### Changed

- Automatically retry DELETE requests too as they are idempotent (audit trail will not
  change if issued twice)


## [0.3.0] - 2021-10-07

### Changed

- Switch token management to localStorage in `analytics_connect()`.
- API requests are now retried on errors, when possible.

### Added

- Add an overwrite flag to `make_package()` so that we only explicitly overwrite an
  existing package.
- Add ability to control location of temporary files.


## [0.2.9] - 2021-03-10

- Updated packages (including cryptography) for security.
- Fix bugs in untar_to_dir and download_to_file which were both using kwarg `target`
  rather than `target_dir` or `target_file` respectively.


## [0.2.8] - 2021-03-03

### Added

- Option to include the zone when uploading blobs.


## [0.2.7] - 2021-01-19

### Fixed

- Fix bug where the "Content-type" header for views returning CSV also has the charset
  option ("text/csv; charset=UTF-8").


## [0.2.6] - 2020-09-12

### Added

- Downloading and uploading blobs to/from files is now streamed rather than using
  temporary memory.


## [0.2.5] - 2020-09-12

### Fixed

- Fix bug where dbctl_download_data ignored passed in filename.


## [0.2.4] - 2020-09-08

### Added

- A changelog!

### Fixed

- Removed traceback from users without roles. Fixes bug #25.
