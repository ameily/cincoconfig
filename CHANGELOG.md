# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Fixed

- Properly evaluate nested `IncludeField`


## [0.4.0] - 2020-07-25
### Added
- `Schema.__getitem__()` implementation to get a schema field programmatically.
- `Schema.get_all_fields()` to recursively get all the fields and nested fields from a schema.

### Changed
- The Schema fields are now stored in an `OrderedDict` so that the original order that the fields
  were added to the Schema is preserved when tterating over the Schema's fields, via `iter()` or
  the new `get_all_fields()`.
