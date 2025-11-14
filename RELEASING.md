# Release Process

## Preliminary

- Check for breaking API changes.
```sh
sphinx-build -b text ./bugwarrior/docs new-docs-build ./bugwarrior/docs/other-services/api.rst
git checkout $LATEST_RELEASE
sphinx-build -b text ./bugwarrior/docs prev-docs-build ./bugwarrior/docs/other-services/api.rst
diff ./prev-docs-build/other-services/api.txt ./new-docs-build/other-services/api.txt
```
- Update CHANGELOG.rst.
- Update version in pyproject.toml.

## Release

- Git tag.
```sh
git tag X.Y.Z
git push upstream tag X.Y.Z
```
- Publish to Pypi.
- Navigate to the tag in the GitHub releases UI and create a release, probably just copying from the CHANGELOG.

## Postliminary

- Update version in pyproject.toml to `X.Y.Z.post`.
