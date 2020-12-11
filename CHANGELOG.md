# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.6.1] - 2020-12-10
### Added
- `Config._container` field to store nested configuration object's parent container
  (`ContainerValue`), which improves the accuracy and completeness of field paths.


## [v0.6.0] - 2020-11-05
### Added
- `Field.sensitive` property to mark a value as sensitive.
- `Config.to_tree()` now supports masking sensitive values (`sensitive_mask` parameter) and
  including virtual fields in the tree (`virtual` parameter).

### Changed
- `StringField` now only accepts string values. Prior to this release, all input values were
  coerced to a string, via `str(value)`. This was causing inconsistencies and non-intuitive
  behavior for fields that inherited from `StringField`.
- Refactor `ListProxy` to inherit from `list`.

### Fixed
- `ListField` now handles empty or `None` values.


## [v0.5.0] - 2020-10-31
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
