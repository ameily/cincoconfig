# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- `StringField`: Provide available choices in the raised exception when value is not valid.
- `Field.friendly_name()` to retrieve the friendly name of the field, either the `Field.name` or
  the full path to the field in the configuration, `Field.full_path()`
- `Config.__contains__()` to check if a configuration has a field value set.


### Changed
- All exceptions raised during validation are now wrapped in a `ValidationError` exception that
  contains the friendly name or full path to the field.
- `SecureField`: Do not encrypt empty string or null values.


### Fixed
- Properly evaluate nested `IncludeField`.
- `FilenameField`: Properly validate and handle required filename values.
- `ListField`: Properly handle a list of complex or Schema objects.
- `ListField`: Wrap the default `ListField` value in a `ListProxy` object.
- `SecureField`: Properly load `best` encrypted values.
- `SecureField`: Resolve `best` encryption method to a concrete method (aes or xor) during
  encryption.


## [0.4.0] - 2020-07-25
### Added
- `Schema.__getitem__()` implementation to get a schema field programmatically.
- `Schema.get_all_fields()` to recursively get all the fields and nested fields from a schema.

### Changed
- The Schema fields are now stored in an `OrderedDict` so that the original order that the fields
  were added to the Schema is preserved when tterating over the Schema's fields, via `iter()` or
  the new `get_all_fields()`.
