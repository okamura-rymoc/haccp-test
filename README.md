# HACCP 衛生管理点検アプリ（Streamlit + Docker）

食品取扱者の衛生管理点検を記録・一覧・PDF出力する Streamlit アプリです。  
JST（日本時間）で保存し、時刻表示は `HH:MM:SS` に統一しています。

## ローカルでの実行方法（Docker）

```bash
# ビルド
docker build -t haccp-app .

# 実行
docker run -it --rm -p 8501:8501 haccp-app
```

ブラウザで http://localhost:8501 を開くと利用できます。

## ファイル構成

```
.
├─ haccp_1_app.py      # アプリ本体
├─ requirements.txt    # 依存ライブラリ
├─ Dockerfile          # Docker用定義
├─ .dockerignore       # Dockerビルド除外
├─ .gitignore          # Git除外
└─ README.md           # 説明
```

## デプロイのヒント

- **Streamlit Community Cloud**: このリポジトリを指定すれば動作します。
- **Render / 他PaaS**: Python 3.13 を選び、Start command を  
  `streamlit run haccp_1_app.py --server.port $PORT --server.address 0.0.0.0`  
  に設定してください。

## ライセンス
必要に応じて LICENSE を追加してください（例: MIT）。
