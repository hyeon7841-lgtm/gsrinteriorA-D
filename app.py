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

def ensure_vendor_mapping():
    c.execute("DROP TABLE IF EXISTS vendor_mapping")
    c.execute("""
    CREATE TABLE IF NOT EXISTS vendor_mapping (
        부문 TEXT,
        지역팀 TEXT,
        영업팀 TEXT,
        업체명 TEXT
    )
    """)
    conn.commit()

ensure_vendor_mapping()

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
if "last_menu" not in st.session_state:
    st.session_state.last_menu = None

# =====================================================
# 사이드바
# =====================================================
menu = st.sidebar.radio("메뉴", ["집기입고 문의", "입고문의 처리", "데이터 관리"])

if st.session_state.last_menu == "데이터 관리" and menu != "데이터 관리":
    st.session_state.admin_auth = False
st.session_state.last_menu = menu

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
            연락처 = st.text_input("연락처")
            점포명 = st.text_input("점포명")
            요청집기목록 = st.text_area("요청집기목록")

        if st.form_submit_button("문의 등록"):
            연락처 = 연락처.replace("-", "").strip()
            if 점포명.endswith("점"):
                점포명 = 점포명[:-1]

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
    df = pd.read_sql("SELECT * FROM requests", conn)
    df_view = df.drop(columns=["연락처"], errors="ignore")
    st.dataframe(df_view, use_container_width=True, hide_index=True)

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
        df = pd.read_sql(
            "SELECT * FROM requests WHERE 업체명=? ORDER BY id DESC",
            conn,
            params=(st.session_state.vendor,)
        )
        st.dataframe(df.drop(columns=["연락처"], errors="ignore"), hide_index=True)

        미처리 = df[df["입고완료"] == 0]
        if not 미처리.empty:
            선택ID = st.selectbox("처리할 문의 ID", 미처리["id"])
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

        # ---------- 분석 ----------
        st.subheader("📈 처리현황 분석")
        기준 = st.radio("분석 기준", ["업체명", "부문", "지역팀"], horizontal=True)

        summary = df.groupby(기준).agg(
            전체건수=("id", "count"),
            완료건수=("입고완료", "sum")
        )
        summary["처리율(%)"] = (summary["완료건수"] / summary["전체건수"] * 100).round(1)
        st.dataframe(summary, use_container_width=True)
        st.bar_chart(summary["처리율(%)"])

        # ---------- 업체 매칭 ----------
        st.divider()
        st.subheader("🏭 업체 매칭 관리")

        with st.form("mapping_form"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                m부문 = st.selectbox("부문", 부문_리스트)
            with col2:
                m지역 = st.selectbox("지역팀", 지역팀_리스트)
            with col3:
                m영업 = st.selectbox("영업팀", 영업팀_리스트)
            with col4:
                m업체 = st.text_input("업체명")

            if st.form_submit_button("매칭 추가/수정"):
                c.execute("""
                DELETE FROM vendor_mapping
                WHERE 부문=? AND 지역팀=? AND 영업팀=?
                """, (m부문, m지역, m영업))
                c.execute(
                    "INSERT INTO vendor_mapping VALUES (?, ?, ?, ?)",
                    (m부문, m지역, m영업, m업체)
                )
                conn.commit()

                # 🔄 기존 문의 업체명 동기화
                c.execute("""
                UPDATE requests
                SET 업체명=?
                WHERE 부문=? AND 지역팀=? AND 영업팀=?
                """, (m업체, m부문, m지역, m영업))
                conn.commit()

                st.success("매칭 및 기존 문의 연동 완료")
                st.rerun()

        map_df = pd.read_sql("SELECT * FROM vendor_mapping", conn)
        st.dataframe(map_df, hide_index=True)
