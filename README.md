# GoogleMap用 都市計画決定GISデータ

## 概要

国土交通省が公開している「[都市計画決定GISデータ](https://www.mlit.go.jp/toshi/tosiko/toshi_tosiko_tk_000087.html)」（shape形式）を、Googleマイマップで利用できるようkml形式に変換した。

変換済の項目は以下。

- 都市計画区域
- 区域区分（市街化区域、市街化調整区域）
- 用途地域（工業専用地域、商業地域等）

[kml_google_map](kml_google_map)内に、都道府県別に格納している。

## kml変換

### 変換方法

[notebook](notebook)にJupyterNotebookを格納しているので詳しくはそちらを参照。

色設定等もここでテストできる。

### 一括処理

次のファイルを実行すれば、全都道府県のデータを一括で変換＆保存できる。

- [01_都市計画区域.py](01_都市計画区域.py)
- [02_区域区分.py](02_区域区分.py)
- [03_用途地域.py](03_用途地域.py)


## 仮想環境

venvをアクティベイトして、`pip install -r requirements.txt`
