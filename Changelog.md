# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [unreleased]
### Added
### Changed
### Removed
### Fixed

## [v0.4.0.0] - 2022-02-04
### Added
- Support `--recurrent-only` option for `fina list` command.
### Changed
- The upstream `financeager` dependency is required as v1.0.0 or higher.

## [v0.3.4.1 - 2021-12-30]
### Fixed
- Correctly generate release notes when running Github release action.

## [v0.3.4.0 - 2021-12-28]
### Changed
- The upstream `financeager` dependency is required as lower than v0.26.3.0.
- Extend CLI help for `web-version` command.

## [v0.3.3.0 - 2021-12-14]
### Added
- Provide `web-version` CLI command to query information about financeager software version installed on server (#2).
### Changed
- The upstream `financeager` dependency is required as v0.26.2.0 or higher.

## [v0.3.2.0 - 2021-12-12]
### Added
- Officially support Python 3.10.
### Changed
- Use more modern packaging structure/methods.
### Fixed
- Relax `financeager` dependency.

## [v0.3.1.0 - 2021-01-22]
### Changed
- The upstream `financeager` dependency is updated to v0.26.0.0. HTTP error codes are more consistent now.

## [v0.3.0.0] - 2021-01-01
### Changed
- The upstream `financeager` dependency is updated to v0.25.0.0. The REST API endpoint `/periods` is renamed to `/pockets`.
- CI testing is performed using Github actions instead of Travis.

## [v0.2.0.0] - 2020-12-06
### Added
- Migrated all webservice-related functionality from financeager base package.

## [v0.1.0.0] - 2020-10-30
### Added
- First (testing) release
