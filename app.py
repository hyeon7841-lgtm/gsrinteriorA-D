import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# =====================================================
# 기본 설정
# =====================================================
st.set_page_config(page_title="집기입고 관리", layout="wide")
DB_PATH = "data.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_conn()
c = conn.cursor()

# =====================================================
# 테이블
# =====================================================
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
    입고완료 INTEGER DEFAULT 0,
    입고완료일 TEXT
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

# =====================================================
# 옵션
# =====================================================
부문_리스트 = [f"{i}부문" for i in range(1, 7)]
지역팀_리스트 = ["1지역", "2지역", "3지역", "4지역", "신선영업1", "신선영업2"]
영업팀_리스트 = [f"{i}팀" for i in range(1, 10)]

# =====================================================
# 업체 계정
# =====================================================
VENDOR_USERS = {
    "한영냉동": "한영1!",
    "태민냉동": "태민1!",
    "우단시스템": "우단시스템1!"
}

# =====================================================
# 세션
# =====================================================
if "vendor" not in st.session_state:
    st.session_state.vendor = None
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

# =====================================================
# 사이드바
# =====================================================
menu = st.sidebar.radio(
    "메뉴",
    ["집기입고 문의", "입고문의 처리", "데이터 관리"]
)

# =====================================================
# 1️⃣ 집기입고 문의
# =====================================================
if menu == "집기입고 문의":
    st.header("📦 집기입고 문의")

    with st.form("request_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            부문 = st.selectbox("부문", 부문_리스트)
            지역팀 = st.selectbox("지역팀", 지역팀_리스트)
            영업팀 = st.selectbox("영업팀", 영업팀_리스트)
            담당자명 = st.text_input("담당자명")

        with col2:
            연락처 = st.text_input("연락처 (숫자만)")
            점포명 = st.text_input("점포명 (점 제외)")
            요청집기목록 = st.text_area("요청집기목록")

        if st.form_submit_button("문의 등록"):
            if "-" in 연락처:
                st.warning("연락처는 숫자만 입력해주세요 (- 제외)")
                st.stop()
            if 점포명.endswith("점"):
                st.warning("점포명에 '점'은 입력하지 말아주세요")
                st.stop()

            vendor = c.execute(
                "SELECT 업체명 FROM vendor_mapping WHERE 부문=? AND 지역팀=? AND 영업팀=?",
                (부문, 지역팀, 영업팀)
            ).fetchone()
            업체명 = vendor[0] if vendor else "미지정"

            c.execute("""
            INSERT INTO requests
            (부문, 지역팀, 영업팀, 담당자명, 연락처, 점포명,
             요청집기목록, 등록일, 업체명)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                부문, 지역팀, 영업팀, 담당자명,
                연락처, 점포명,
                요청집기목록,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                업체명
            ))
            conn.commit()
            st.success("등록 완료")
            st.rerun()

    st.divider()
    st.subheader("📋 집기입고 문의 현황")

    search = st.text_input("점포명 검색")
    query = "SELECT * FROM requests"
    df = pd.read_sql(query, conn)

    if search:
        df = df[df["점포명"].str.contains(search, na=False)]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ⏳ 처리중")
        st.dataframe(df[df["입고완료"] == 0], use_container_width=True)
    with col2:
        st.markdown("### ✅ 입고완료")
        st.dataframe(df[df["입고완료"] == 1], use_container_width=True)

# =====================================================
# 2️⃣ 입고문의 처리
# =====================================================
if menu == "입고문의 처리":
    st.header("🏭 입고문의 처리")

    if st.session_state.vendor is None:
        vid = st.text_input("업체 ID")
        vpw = st.text_input("비밀번호", type="password")

        if st.button("로그인"):
            for k, v in VENDOR_USERS.items():
                if k.lower() == vid.strip().lower() and v == vpw:
                    st.session_state.vendor = k
                    st.rerun()
            st.error("로그인 실패")
    else:
        st.success(f"로그인 업체: {st.session_state.vendor}")

        df = pd.read_sql(
            "SELECT * FROM requests WHERE 업체명=? ORDER BY id DESC",
            conn,
            params=(st.session_state.vendor,)
        )

        st.subheader("📋 등록된 문의 목록")
        st.dataframe(df, use_container_width=True)

        미처리 = df[df["입고완료"] == 0]
        if len(미처리) > 0:
            선택ID = st.selectbox("처리할 문의 선택 (ID)", 미처리["id"].tolist())
            예정일 = st.date_input("예정입고일", date.today())
            완료 = st.checkbox("입고완료")

            if st.button("처리 저장"):
                완료일 = date.today().strftime("%Y-%m-%d") if 완료 else None
                c.execute("""
                UPDATE requests
                SET 예정입고일=?, 입고완료=?, 입고완료일=?
                WHERE id=?
                """, (예정일.strftime("%Y-%m-%d"), int(완료), 완료일, 선택ID))
                conn.commit()
                st.success("처리 완료")
                st.rerun()

# =====================================================
# 3️⃣ 데이터 관리
# =====================================================
if menu == "데이터 관리":
    st.header("📊 데이터 관리")

    if not st.session_state.admin_auth:
        pw = st.text_input("비밀번호", type="password")
        if st.button("확인"):
            if pw in ["시설", "tltjf"]:
                st.session_state.admin_auth = True
                st.rerun()
            else:
                st.error("비밀번호 오류")
    else:
        df = pd.read_sql("SELECT * FROM requests", conn)

        st.subheader("업체별 처리율")
        summary = df.groupby("업체명").agg(
            전체=("id", "count"),
            완료=("입고완료", "sum")
        )
        summary["완료율(%)"] = (summary["완료"] / summary["전체"] * 100).round(1)
        st.dataframe(summary)

        st.subheader("업체 매칭 관리")
        map_df = pd.read_sql("SELECT * FROM vendor_mapping", conn)
        edited = st.data_editor(map_df, num_rows="dynamic", use_container_width=True)

        if st.button("매칭 저장"):
            c.execute("DELETE FROM vendor_mapping")
            for _, r in edited.iterrows():
                c.execute(
                    "INSERT INTO vendor_mapping VALUES (?, ?, ?, ?)",
                    (r["부문"], r["지역팀"], r["영업팀"], r["업체명"])
                )
            conn.commit()
            st.success("저장 완료")
