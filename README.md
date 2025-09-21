# HACCP 衛生管理点検アプリ（Streamlit）

食品取扱者の衛生管理点検を記録・一覧・PDF出力する Streamlit アプリです。  
JST（日本時間）で保存し、時刻表示は `HH:MM:SS` に統一しています。

## ローカル実行

```bash
# 1) 任意のフォルダで仮想環境を作成（任意）
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

# 2) 依存をインストール
pip install -r requirements.txt

# 3) アプリを起動
streamlit run haccp_1_app.py
```

- 初回起動時、同ディレクトリに `haccp_1_logs.db` を作成します（SQLite）。
- ログは `haccp_1_app.log` に出力されます。

## ファイル構成（例）

```
.
├─ haccp_1_app.py         # アプリ本体
├─ requirements.txt       # 依存ライブラリ
├─ .gitignore             # 不要ファイルの除外設定
└─ README.md              # 説明
```

## デプロイのヒント

### Streamlit Community Cloud
- リポジトリを公開し、`haccp_1_app.py` をメインファイルに指定するだけで動きます。

### Render / 他の PaaS
- Python 3.9+ を選択
- Start command: `streamlit run haccp_1_app.py --server.port $PORT --server.address 0.0.0.0`
- 環境変数に `TZ=Asia/Tokyo` を設定するとより安心（アプリ側も JST 固定済み）

## ライセンス
必要に応じて LICENSE を追加してください（例：MIT）。
