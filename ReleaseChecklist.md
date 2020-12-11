- [ ] Update changelog
- [ ] Bump `version.py`
- [ ] Run tox
  ```
  tox -e py37
  ```

- [ ] Build the packages
  ```
  python setup.py bdist_wheel sdist
  ```

- [ ] Check the packages
  ```
  twine check dist/*
  ```

- [ ] Upload the packages to to TestPyPi
  ```
  twine upload --repository-url https://test.pypi.org/legacy/ dist/*
  ```

- [ ] Verify everything looks good by going to https://test.pypi.org/project/cincoconfig
- [ ] Upload to PyPI
  ```
  twine upload dist/*
  ```

- [ ] Tag the release
  ```
  git tag vX.Y.Z
  git push origin vX.Y.Z
  ```
