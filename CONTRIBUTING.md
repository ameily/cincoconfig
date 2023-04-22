# Contibuting

All contributions are welcome! Feel free to open issues and submit pull requests as needed.

## Development Environment

cincoconfig uses poetry for dependency management and several tools for code quality checks:

- [ruff](https://pypi.org/project/ruff/) - linting
- [pyright](https://pypi.org/project/pyright/) - type checking
- [black](https://pypi.org/project/black/) - formatting

To get started:

1. [Install Poetry](https://python-poetry.org/docs/)
1. Install dependencies and feature packages.
   ```
   poetry install --with dev,yaml,crypto,bson
   ```

There are several `poe` commands available that wil help during development:

```bash
# format all Python code
poetry run poe format

# build sphinx HTML docs
poetry run poe build-docs

# check format
poetry run poe check-format

# check typing
poetry run poe check-typing

# lint
poetry run poe lint

# unit tests
poetry run poe tests

# entire CI chain (check-format, check-typing, lint, tests)
poetry run poe ci
```
