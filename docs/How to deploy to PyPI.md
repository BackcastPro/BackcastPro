## How to deploy to PyPI

User Guide:
https://packaging.python.org/en/latest/tutorials/packaging-projects/

### Generating distribution archives

generate distribution packages for the package. 
```
python -m build
```

### Uploading the distribution archives

Finally, it’s time to upload your package to the Python Package Index!
```
python -m twine upload --repository pypi dist/*
```

You will be prompted for an API [token](https://pypi.org/manage/account/#api-tokens). Use the token value, including the pypi- prefix. Note that the input will be hidden, so be sure to paste correctly.
```
Enter your API token: 
```

After the command completes, you should see output similar to this:

```
Uploading distributions to https://test.pypi.org/legacy/
Enter your API token:
Uploading example_package_YOUR_USERNAME_HERE-0.0.1-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.2/8.2 kB • 00:01 • ?
Uploading example_package_YOUR_USERNAME_HERE-0.0.1.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 6.8/6.8 kB • 00:00 • ?
```

おめでとう