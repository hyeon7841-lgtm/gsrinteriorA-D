import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, date

st.set_page_config(page_title="집기입고 현황", layout="wide")

DB = "data.db"

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

conn = get_conn()
c = conn.cursor()

# ==================================================
# 테이블 생성
# ==================================================
c.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    부문 TEXT,
    지역팀 TEXT,
    영업팀 TEXT,
    담당자명 TEXT,
    연락처 TEXT,
    점포명 TEXT,
    요청집기목록 TEXT,
    등록일 TEXT,
    업체명 TEXT,
    예정입고일 TEXT,
    상태 TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS completed_archive (
    id INTEGER,
    부문 TEXT,
    지역팀 TEXT,
    영업팀 TEXT,
    담당자명 TEXT,
    연락처 TEXT,
    점포명 TEXT,
    요청집기목록 TEXT,
    등록일 TEXT,
    업체명 TEXT,
    예정입고일 TEXT,
    상태 TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS vendor_mapping (
    부문 TEXT,
    지역팀 TEXT,
    영업팀 TEXT,
    업체명 TEXT
)
""")

conn.commit()

# ==================================================
# 🔧 컬럼 마이그레이션 (구버전 DB 대응)
# ==================================================
def add_column_if_not_exists(table, column, col_type):
    cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()

for col, typ in [
    ("업체명", "TEXT"),
    ("상태", "TEXT"),
    ("예정입고일", "TEXT")
]:
    add_column_if_not_exists("requests", col, typ)

# ==================================================
# 옵션
# ==================================================
부문목록 = [f"{i}부문" for i in range(1, 7)]
지역팀목록 = ["1지역", "2지역", "3지역", "4지역", "신선영업1", "신선영업2"]
영업팀목록 = [f"{i}팀" for i in range(1, 10)]

업체계정 = {
    "한영냉동": "한영1!",
    "태민냉동": "태민1!",
    "우단시스템": "우단시스템1!"
}

# ==================================================
# 세션
# ==================================================
if "vendor" not in st.session_state:
    st.session_state.vendor = None
if "admin" not in st.session_state:
    st.session_state.admin = False

menu = st.sidebar.radio(
    "메뉴",
    ["집기입고 문의", "입고문의 처리", "데이터 관리"]
)

if menu != "입고문의 처리":
    st.session_state.vendor = None
if menu != "데이터 관리":
    st.session_state.admin = False

# ==================================================
# 1️⃣ 집기입고 문의
# ==================================================
if menu == "집기입고 문의":
    st.header("📦 집기입고 문의")

    with st.form("req_form"):
        col1, col2, col3 = st.columns(3)
        부문 = col1.selectbox("부문", 부문목록)
        지역팀 = col2.selectbox("지역팀", 지역팀목록)
        영업팀 = col3.selectbox("영업팀", 영업팀목록)

        담당자명 = st.text_input("담당자명")
        연락처 = st.text_input("연락처 (- 없이)")
        점포명 = st.text_input("점포명 (점 제외)")
        요청집기목록 = st.text_area("요청집기목록")

        if st.form_submit_button("문의 등록"):
            연락처 = 연락처.replace("-", "")
            if 점포명.endswith("점"):
                점포명 = 점포명[:-1]

            v = c.execute(
                "SELECT 업체명 FROM vendor_mapping WHERE 부문=? AND 지역팀=? AND 영업팀=?",
                (부문, 지역팀, 영업팀)
            ).fetchone()
            업체명 = v[0] if v else "미지정"

            c.execute("""
            INSERT INTO requests
            (부문, 지역팀, 영업팀, 담당자명, 연락처, 점포명,
             요청집기목록, 등록일, 업체명, 상태)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '접수')
            """, (
                부문, 지역팀, 영업팀, 담당자명, 연락처,
                점포명, 요청집기목록,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                업체명
            ))
            conn.commit()
            st.success("문의가 등록되었습니다.")
            st.rerun()

    st.subheader("📋 전체 집기입고 문의 현황")
    df_all = pd.read_sql("SELECT * FROM requests ORDER BY id DESC", conn)
    st.dataframe(df_all, hide_index=True, use_container_width=True)

# ==================================================
# 2️⃣ 입고문의 처리
# ==================================================
if menu == "입고문의 처리":
    st.header("🏭 입고문의 처리")

    if not st.session_state.vendor:
        vid = st.text_input("업체 ID")
        pw = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            if vid in 업체계정 and 업체계정[vid] == pw:
                st.session_state.vendor = vid
                st.rerun()
            else:
                st.error("로그인 실패")
    else:
        st.success(f"로그인 업체 : {st.session_state.vendor}")

        df = pd.read_sql(
            "SELECT * FROM requests WHERE 업체명=? ORDER BY id DESC",
            conn, params=(st.session_state.vendor,)
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("🟥 접수")
            st.dataframe(df[df["상태"] == "접수"], hide_index=True)
        with col2:
            st.subheader("🟨 처리중")
            st.dataframe(df[df["상태"] == "처리중"], hide_index=True)
        with col3:
            st.subheader("🟩 완료")
            st.dataframe(df[df["상태"] == "완료"], hide_index=True)

        st.subheader("✏️ 문의 처리")
        if not df.empty:
            선택ID = st.selectbox("처리할 문의 ID", df["id"])
            예정일 = st.date_input("입고예정일", date.today())
            완료 = st.checkbox("입고완료")

            if st.button("처리 저장"):
                상태 = "완료" if 완료 else "처리중"
                c.execute(
                    "UPDATE requests SET 예정입고일=?, 상태=? WHERE id=?",
                    (예정일.strftime("%Y-%m-%d"), 상태, 선택ID)
                )
                conn.commit()
                st.success("처리되었습니다.")
                st.rerun()
        else:
            st.info("처리할 문의가 없습니다.")

# ==================================================
# 3️⃣ 데이터 관리
# ==================================================
if menu == "데이터 관리":
    st.header("📊 데이터 관리")

    if not st.session_state.admin:
        pw = st.text_input("관리자 비밀번호", type="password")
        if st.button("확인"):
            if pw in ["시설", "tltjf"]:
                st.session_state.admin = True
                st.rerun()
            else:
                st.error("비밀번호 오류")
    else:
        df = pd.read_sql("SELECT * FROM requests", conn)

        st.subheader("📋 현재 문의 현황표")
        st.dataframe(df, hide_index=True, use_container_width=True)

        st.subheader("📈 업체별 처리현황")
        if not df.empty and "업체명" in df.columns and "상태" in df.columns:
            g = df.groupby("업체명").agg(
                전체=("id", "count"),
                완료=("상태", lambda x: (x == "완료").sum())
            ).reset_index()
            g["처리율"] = (g["완료"] / g["전체"] * 100).round(1)

            bar = alt.Chart(g).mark_bar().encode(
                x="업체명",
                y=alt.Y("전체", title="건수")
            )
            line = alt.Chart(g).mark_line(color="red").encode(
                x="업체명",
                y=alt.Y("처리율", axis=alt.Axis(title="처리율(%)"))
            )

            st.altair_chart(
                alt.layer(bar, line).resolve_scale(y="independent"),
                use_container_width=True
            )
        else:
            st.info("그래프를 표시할 데이터가 없습니다.")

        st.subheader("📦 완료건 → 완료보관함 이동")
        if st.button("입고완료 보관"):
            c.execute("""
            INSERT INTO completed_archive
            SELECT * FROM requests WHERE 상태='완료'
            """)
            c.execute("DELETE FROM requests WHERE 상태='완료'")
            conn.commit()
            st.success("완료보관함으로 이동 완료")
            st.rerun()

        st.subheader("❌ 잘못 접수된 문의 삭제")
        if not df.empty:
            del_id = st.selectbox("삭제할 문의 ID", df["id"])
            if st.button("문의 삭제"):
                c.execute("DELETE FROM requests WHERE id=?", (del_id,))
                conn.commit()
                st.success("삭제 완료")
                st.rerun()
