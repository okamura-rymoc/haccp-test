# -*- coding: utf-8 -*-
"""
食品取扱者の衛生管理点検アプリ（Streamlit 版）
- チェック項目：適 / 不適 / 未選択（未選択が含まれる場合は保存不可）
- 記録日は本日で固定（表示のみ・変更不可）、記録時刻も表示
- 氏名入力必須・コメント欄
- 入力日時は日付＋時刻（秒）で自動保存（created_at）
- 検索・一覧は「記録日／記録時間／氏名／①〜⑧／コメント（右端）」表示
- PDFは横向きA4の表形式・日本語フォント（環境依存）
- PDFにページ番号（ページ X）を下中央に表示
- PDFの生成日時の直下に指定行を追加（右寄せ）
"""
import os
import io
import json
import sqlite3
import logging
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import streamlit as st

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import mm
from zoneinfo import ZoneInfo  # ← JST固定用

# ================== タイムゾーン ==================
JST = ZoneInfo("Asia/Tokyo")

# ================== パス等 ==================
SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = str(SCRIPT_DIR / "haccp_1_logs.db")
LOG_PATH = SCRIPT_DIR / "haccp_1_app.log"


# ================== ログ設定 ==================
logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
    force=True,
)

# ================== ReportLab 日本語フォント登録 ==================
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
JP_FONT = "HeiseiKakuGo-W5"

# ================== チェック項目（8項目） ==================
CHECK_ITEMS = [
    "①下痢、嘔吐はないか。",
    "②発熱はないか。",
    "③手指に化膿創はないか。",
    "④爪は短く切ってあるか。",
    "⑤衛生的な服装か。",
    "⑥身だしなみは適切か。",
    "⑦ｱｸｾｻﾘｰや時計は外してあるか。",
    "⑧同居家族に下痢・嘔吐はないか。",
]
SHORT_LABELS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"]

EXPLANATION_LINE = (
    "説明：①下痢、嘔吐はないか。②発熱はないか。③手指に化膿創はないか。④爪は短く切ってあるか。"
    "⑤衛生的な服装か。⑥身だしなみは適切か。⑦ｱｸｾｻﾘｰや時計は外してあるか。⑧同居家族に下痢・嘔吐はないか。"
)

# ================== DB ユーティリティ ==================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                items_json TEXT NOT NULL,
                comment TEXT,
                staff_name TEXT
            )
            """
        )
        conn.commit()


# ================== UI 要素 ==================
@dataclass
class NewRecord:
    staff_name: str
    items: List[str]
    comment: str


def render_form():
    st.subheader("記録入力")

    # 入力を初期化できるようにフォーム用の nonce を利用
    nonce = st.session_state.get("form_nonce", 0)

    with st.form(f"form_{nonce}", clear_on_submit=False):
        staff_name = st.text_input("氏名", "", key=f"staff_name_{nonce}")
        st.write("**チェック項目**（それぞれ 適 / 不適 / 未選択）")
        selections = {}
        for i, item in enumerate(CHECK_ITEMS):
            col_label, col_opts = st.columns([6, 4])
            with col_label:
                st.markdown(f"**{item}**")
            with col_opts:
                selections[item] = st.radio(
                    label=item,
                    options=["適", "不適", "未選択"],
                    index=2,
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"radio_{nonce}_{i}",
                )
        comment = st.text_area("コメント（任意）", "", height=80, key=f"comment_{nonce}")
        submitted = st.form_submit_button("保存")

    if submitted:
        # 1) 氏名必須
        if not staff_name.strip():
            st.error("氏名を入力してください。")
            return None

        # チェック状態を評価
        unselected_idx = [i for i, item in enumerate(CHECK_ITEMS, start=1) if selections.get(item) == "未選択"]
        ng_idx = [i for i, item in enumerate(CHECK_ITEMS, start=1) if selections.get(item) == "不適"]

        # 2) 未選択がある場合：保存不可＆注意
        if unselected_idx:
            st.warning("未選択の項目があります。全て選択してください：" + "、".join(map(str, unselected_idx)))
            return None

        # 3) 不適がある場合：pendingに保持し、OKボタンで保存
        if ng_idx:
            st.session_state["ng_notice"] = {"items": []}  # 番号は表示しない仕様
            st.session_state["pending_record"] = {
                "staff_name": staff_name.strip(),
                "selections": selections,
                "comment": comment.strip(),
            }
            return None

        # 4) 全て適：保存して初期化
        items_json = json.dumps({k: v for k, v in selections.items()}, ensure_ascii=False)
        record = NewRecord(staff_name=staff_name.strip(), items=list(selections.values()), comment=comment.strip())
        save_record(record, items_json)
        st.success("保存しました。")
        st.session_state.pop("ng_notice", None)
        # 入力初期化：nonce を進めて rerun（氏名空、各ラジオ未選択に戻す）
        st.session_state["form_nonce"] = nonce + 1
        st.rerun()


def render_ng_notice():
    """不適がある場合の確認。OKでpendingを保存する"""
    notice = st.session_state.get("ng_notice")
    if not notice:
        return
    holder = st.container()
    holder.error("不適の項目があります。責任者へ必ず報告してください。")
    if holder.button("OK", key="ng_ok"):
        # pending があれば保存して初期化
        pending = st.session_state.pop("pending_record", None)
        if pending:
            items_json = json.dumps({k: v for k, v in pending["selections"].items()}, ensure_ascii=False)
            record = NewRecord(
                staff_name=pending.get("staff_name", "").strip(),
                items=list(pending["selections"].values()),
                comment=pending.get("comment", "").strip(),
            )
            save_record(record, items_json)
            st.success("保存しました。")
        # メッセージ消去＆入力初期化
        st.session_state.pop("ng_notice", None)
        st.session_state["form_nonce"] = st.session_state.get("form_nonce", 0) + 1
        st.rerun()


def save_record(record: NewRecord, items_json: str):
    """JSTで保存し、+09:00のオフセットはDB文字列に含めない"""
    now = datetime.now(JST)
    today = now.date().isoformat()
    created = now.strftime("%Y-%m-%dT%H:%M:%S")  # ← +09:00 を付けない
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO records (record_date, created_at, items_json, comment, staff_name) VALUES (?, ?, ?, ?, ?)",
            (today, created, items_json, record.comment, record.staff_name),
        )
        conn.commit()


# === 表示整形ユーティリティ ===
def to_hms(created_at: str) -> str:
    """
    ISO形式（+09:00付き/無しの両方）から「HH:MM:SS」だけを返す。
    """
    try:
        dt = datetime.fromisoformat(created_at)  # +09:00付きでもOK
        return dt.strftime("%H:%M:%S")
    except ValueError:
        return created_at[11:19] if len(created_at) >= 19 else created_at


# ================== 一覧＆PDF ==================
def fetch_rows(start: str, end: str) -> List[Tuple]:
    with get_conn() as conn:
        q = (
            "SELECT id, record_date, created_at, items_json, comment, staff_name "
            "FROM records WHERE record_date BETWEEN ? AND ? "
            "ORDER BY record_date ASC, created_at ASC, id ASC"
        )
        return list(conn.execute(q, (start, end)))


def make_pdf_buffer(rows: List[Tuple], title: str = "食品取扱者の衛生管理点検表") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=24,
        bottomMargin=24,
    )

    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    styles = getSampleStyleSheet()
    for s in styles.byName.values():
        s.fontName = JP_FONT

    title_style = styles["Title"]
    title_style.fontName = JP_FONT
    title_style.alignment = TA_LEFT
    normal = styles["Normal"]
    normal.fontName = JP_FONT

    story = []
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 6))
    # JSTで生成日時を表示
    story.append(Paragraph(datetime.now(JST).strftime("生成日時: %Y-%m-%d %H:%M:%S"), normal))
    # 指定行を追加（右寄せ）
    story.append(Paragraph("<para alignment='right'>株式会社辰馬コーポレーション　おず おむすび かふぇ　　責任者確認：____________________　　　　　確認日：______________</para>", normal))
    story.append(Spacer(1, 8))

    headers = [
        Paragraph("<para alignment='center'>#</para>", normal),
        Paragraph("<para alignment='center'>記録日</para>", normal),
        Paragraph("<para alignment='center'>記録時間</para>", normal),
        Paragraph("<para alignment='center'>氏名</para>", normal),
    ] + [Paragraph(f"<para alignment='center'>{lbl}</para>", normal) for lbl in SHORT_LABELS] + [Paragraph("<para alignment='center'>コメント</para>", normal)]
    data: List[List] = [headers]

    for i, (rid, rdate, created_at, items_json, comment, staff_name) in enumerate(rows, start=1):
        items = json.loads(items_json)
        rec_time = to_hms(created_at)  # ← 表示はHH:MM:SSに統一
        row = [str(i), rdate, rec_time, staff_name or "-"]
        for item in CHECK_ITEMS:
            row.append(items.get(item, "未選択"))
        row.append(Paragraph(comment or "-", normal))
        data.append(row)

    # ページ幅に合わせてコメント列を可変化（残り幅をすべてコメント列へ）
    page_w, _ = landscape(A4)
    usable_w = page_w - doc.leftMargin - doc.rightMargin
    fixed = [20, 60, 60, 80] + [30] * 8
    fixed_total = sum(fixed)
    comment_w = max(120, usable_w - fixed_total)
    col_widths = fixed + [comment_w]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), JP_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "RIGHT"),
            ("ALIGN", (1, 1), (3, -1), "CENTER"),
            ("ALIGN", (4, 1), (11, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ])
    )

    story.append(table)
    story.append(Spacer(1, 6))
    story.append(Paragraph(EXPLANATION_LINE, normal))

    def add_footer(canvas, doc_obj):
        canvas.setFont(JP_FONT, 8)
        from reportlab.lib.units import mm as _mm
        w, h = landscape(A4)
        canvas.drawCentredString(w / 2.0, 10 * _mm, f"ページ {canvas.getPageNumber()}")

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


# ================== Streamlit UI ==================
def render_search():
    st.subheader("検索・一覧")
    # “本日”はJST基準
    today = datetime.now(JST).date().isoformat()
    start = st.date_input("開始日", value=date.fromisoformat(today))
    end = st.date_input("終了日", value=date.fromisoformat(today))

    rows = fetch_rows(start.isoformat(), end.isoformat())
    if rows:
        df = pd.DataFrame([
            {
                "#": i,
                "記録日": rdate,
                "記録時間": to_hms(created_at),  # ← 時刻整形
                "氏名": staff or "-",
                **{lbl: json.loads(items_json).get(item, "未選択") for lbl, item in zip(SHORT_LABELS, CHECK_ITEMS)},
                "コメント": comment or "-",
            }
            for i, (rid, rdate, created_at, items_json, comment, staff) in enumerate(rows, start=1)
        ])
        st.dataframe(df, width="stretch")

        if st.button("PDFを作成"):
            pdf = make_pdf_buffer(rows)
            st.download_button("PDFをダウンロード", data=pdf, file_name=f"haccp_{start}_{end}.pdf", mime="application/pdf")
    else:
        st.info("データがありません。")


def main():
    st.set_page_config(page_title="食品取扱者の衛生管理", layout="wide")
    init_db()

    st.title("食品取扱者の衛生管理点検アプリ")

    tab1, tab2 = st.tabs(["記録入力", "検索・一覧"])
    with tab1:
        render_form()
        render_ng_notice()
    with tab2:
        render_search()


if __name__ == "__main__":
    main()
