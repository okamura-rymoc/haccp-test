# HACCP 衛生管理（Streamlit）— GitHub/Render デプロイ手順

## 収録ファイル
- `haccp_1_app.py` … アプリ本体（DB/ログは `DATA_DIR` に保存。既定 `/app/data`）
- `requirements.txt`
- `Dockerfile`

## 環境変数（任意）
- `COMPANY_NAME` … PDFに表示する会社名（既定: 株式会社○○○○○）
- `FACTORY_NAME` … PDFに表示する工場名（既定: △△△△工場）
- `DATA_DIR` … 変更不要（既定 `/app/data`）

## GitHub へのアップロード
1. このフォルダ内の4ファイルをそのまま GitHub の **リポジトリ直下** にアップロード
2. Render ダッシュボード → **New > Web Service**
3. リポジトリを選択すると **Docker** として認識
4. （任意）Environment Variables に `COMPANY_NAME` `FACTORY_NAME` を追加
5. （推奨）**Disks** で Persistent Disk を `/app/data` にマウント
6. デプロイ後、**Settings > Custom Domains** で `haccp-xxx.rymoc.co.jp` を追加（ムームードメインでCNAME）

## ローカル確認（任意）
```bash
docker build -t haccp-app .
docker run --rm -p 8501:8501 -v $(pwd)/data:/app/data   -e COMPANY_NAME="株式会社テスト" -e FACTORY_NAME="第一工場" haccp-app
# → http://localhost:8501
```