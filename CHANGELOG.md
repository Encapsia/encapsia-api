# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

(Nothing yet)

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
