# -*- coding: utf-8 -*-
"""
haccp_1_logs.db を ZIP 圧縮して、Gmail(SMTP) で送信するスクリプト。
Render の Cron Job などで毎日実行してください。

環境変数（Render の Environment Variables で設定）:
  EMAIL_PASS : Gmail の「アプリパスワード」(必須)
任意:
  DB_PATH    : DB ファイルパス（既定: haccp_1_logs.db）
"""
import os, smtplib, zipfile
from pathlib import Path
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

# 固定パラメータ（送信元/送信先/サーバ設定）
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "okamura4476@gmail.com"   # 送信元
MAIL_TO   = "okamura-y@rymoc.co.jp"   # 送信先

# 重要: パスワードは環境変数から読み込む（平文でコードに書かない）
SMTP_PASS = os.getenv("EMAIL_PASS")

# DB パス（任意で上書き可）
DB_PATH = Path(os.getenv("DB_PATH", "haccp_1_logs.db"))

JST = ZoneInfo("Asia/Tokyo")


def make_zip(src: Path) -> Path:
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    zip_path = src.with_name(f"{src.stem}_{ts}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(src, arcname=src.name)
    return zip_path


def send_mail(subject: str, body: str, attach_path: Path):
    if not SMTP_PASS:
        raise RuntimeError("環境変数 EMAIL_PASS が設定されていません。Gmailのアプリパスワードを設定してください。")

    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = MAIL_TO
    msg["Subject"] = subject
    msg.set_content(body)

    data = attach_path.read_bytes()
    msg.add_attachment(data, maintype="application", subtype="zip", filename=attach_path.name)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {DB_PATH.resolve()}")

    zip_path = make_zip(DB_PATH)
    subject = f"[HACCPバックアップ] {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}"
    body = "自動バックアップです。添付のZIPファイルをご確認ください。"
    try:
        send_mail(subject, body, zip_path)
        print(f"Sent: {zip_path.name}")
    finally:
        try:
            zip_path.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    main()
