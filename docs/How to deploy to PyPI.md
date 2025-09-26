## PyPIへのデプロイ方法

ユーザーガイド：
https://packaging.python.org/en/latest/tutorials/packaging-projects/

### 配布アーカイブの生成

パッケージの配布パッケージを生成します。
```
python -m build
```

### 配布アーカイブのアップロード

最後に、パッケージをPython Package Indexにアップロードする時です！
```
python -m twine upload --repository pypi dist/*
```

API [トークン](https://pypi.org/manage/account/#api-tokens)の入力を求められます。pypi-プレフィックスを含むトークン値を使用してください。入力は隠されるため、正しく貼り付けるように注意してください。
```
Enter your API token: 
```

コマンドが完了すると、以下のような出力が表示されます：

```
Uploading distributions to https://test.pypi.org/legacy/
Enter your API token:
Uploading example_package_YOUR_USERNAME_HERE-0.0.1-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.2/8.2 kB • 00:01 • ?
Uploading example_package_YOUR_USERNAME_HERE-0.0.1.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 6.8/6.8 kB • 00:00 • ?
```

おめでとうございます！