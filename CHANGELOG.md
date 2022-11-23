# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [next]

Nothing yet.

## [0.3.3] - ?

### Fixed

- `get_config()` raises a `KeyError` regardless of the error encountered, hiding
  networking or authorization errors. Fixes #48.

## [0.3.2] - 2022-11-09

### Changed

- Allow sending include_deleted|metadata flags in get_blobs()

## [0.3.1] - 2021-10-19

### Changed

- Automatically retry DELETE requests too as they are idempotent (audit trail will not change if issued twice)

## [0.3.0] - 2021-10-07

### Changed

- Switch token management to localStorage in `analytics_connect()`.
- API requests are now retried on errors, when possible.

### Added

- Add an overwrite flag to `make_package()` so that we only explicitly overwrite an existing package.
- Add ability to control location of temporary files.

## [0.2.9] - 2021-03-10

- Updated packages (including cryptography) for security.
- Fix bugs in untar_to_dir and download_to_file which were both using kwarg `target` rather than `target_dir` or `target_file` respectively.

## [0.2.8] - 2021-03-03

### Added

- Option to include the zone when uploading blobs.

## [0.2.7] - 2021-01-19

### Fixed

- Fix bug where the "Content-type" header for views returning CSV also has the charset option ("text/csv; charset=UTF-8").

## [0.2.6] - 2020-09-12

### Added

- Downloading and uploading blobs to/from files is now streamed rather than using temporary memory.

## [0.2.5] - 2020-09-12

### Fixed

- Fix bug where dbctl_download_data ignored passed in filename.

## [0.2.4] - 2020-09-08

### Added

- A changelog!

### Fixed

- Removed traceback from users without roles. Fixes bug #25.
