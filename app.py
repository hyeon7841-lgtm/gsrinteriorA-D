import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="집기입고 관리", layout="wide")
DB_PATH = "data.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_conn()
c = conn.cursor()

# =====================
# DB 테이블
# =====================
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
    업체명 TEXT
)
""")
conn.commit()

# =====================
# 옵션 리스트
# =====================
부문_리스트 = [f"{i}부문" for i in range(1, 7)]
지역팀_리스트 = ["1지역", "2지역", "3지역", "4지역", "신선영업1", "신선영업2"]
영업팀_리스트 = [f"{i}팀" for i in range(1, 10)]

# =====================
# 세션 상태 (비밀번호 유지)
# =====================
if "auth" not in st.session_state:
    st.session_state.auth = False

# =====================
# 사이드바
# =====================
menu = st.sidebar.radio(
    "메뉴",
    ["집기입고 문의", "입고문의 처리", "데이터 관리"]
)

# =========================================================
# 1️⃣ 집기입고 문의
# =========================================================
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
            연락처 = st.text_input("연락처 (숫자만 입력)")
            점포명 = st.text_input("점포명 (점 제외)")
            요청집기목록 = st.text_area("요청집기목록")

        submitted = st.form_submit_button("문의 등록")

        if submitted:
            연락처 = "".join(filter(str.isdigit, 연락처))
            점포명 = 점포명.replace("점", "")

            vendor = c.execute(
                "SELECT 업체명 FROM vendor_mapping WHERE 부문=? AND 지역팀=?",
                (부문, 지역팀)
            ).fetchone()
            업체명 = vendor[0] if vendor else "미지정"

            c.execute("""
            INSERT INTO requests
            (부문, 지역팀, 영업팀, 담당자명, 연락처, 점포명,
             요청집기목록, 등록일, 업체명)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                부문, 지역팀, 영업팀, 담당자명,
                연락처, 점포명, 요청집기목록,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                업체명
            ))
            conn.commit()
            st.success(f"문의 등록 완료 (담당업체: {업체명})")
            st.rerun()

    st.divider()
    st.subheader("📋 집기입고 요청 현황")

    search = st.text_input("🔍 점포명 검색")

    df = pd.read_sql("SELECT * FROM requests ORDER BY id DESC", conn)
    if search:
        df = df[df["점포명"].str.contains(search, na=False)]

    미답변 = df[df["예정입고일"].isna()]
    답변완료 = df[(df["예정입고일"].notna()) & (df["입고완료"] == 0)]
    입고완료 = df[df["입고완료"] == 1]

    st.markdown("### 🕒 문의 등록됨")
    st.dataframe(미답변, use_container_width=True)

    st.markdown("### 📅 답변 등록 완료")
    st.dataframe(답변완료, use_container_width=True)

    st.markdown("### ✅ 입고 완료")
    st.dataframe(입고완료, use_container_width=True)

# =========================================================
# 2️⃣ 입고문의 처리
# =========================================================
if menu == "입고문의 처리":
    st.header("📋 입고문의 처리")

    df = pd.read_sql(
        "SELECT * FROM requests WHERE 입고완료=0 ORDER BY id DESC",
        conn
    )

    st.subheader("현재 문의 목록")
    st.dataframe(df, use_container_width=True)

    if len(df) > 0:
        선택 = st.selectbox(
            "처리할 문의 선택",
            df["id"].tolist(),
            format_func=lambda x: f"ID {x} | {df[df['id']==x]['점포명'].values[0]}"
        )

        예정입고일 = st.date_input("예정입고일", date.today())
        완료 = st.checkbox("입고완료 처리")

        if st.button("저장"):
            완료일 = date.today().strftime("%Y-%m-%d") if 완료 else None

            c.execute("""
            UPDATE requests
            SET 예정입고일=?, 입고완료=?, 입고완료일=?
            WHERE id=?
            """, (
                예정입고일.strftime("%Y-%m-%d"),
                int(완료),
                완료일,
                선택
            ))
            conn.commit()
            st.success("처리 완료")
            st.rerun()
    else:
        st.info("처리할 문의가 없습니다.")

# =========================================================
# 3️⃣ 데이터 관리
# =========================================================
if menu == "데이터 관리":
    st.header("🔐 데이터 관리")

    if not st.session_state.auth:
        pw = st.text_input("비밀번호 입력", type="password")
        if st.button("확인"):
            if pw in ["시설", "tltjf"]:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    else:
        st.success("접근 허용됨")

        df = pd.read_sql("SELECT * FROM requests", conn)

        st.subheader("📊 처리 현황")
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("🏭 업체 매칭 관리")

        mapping_df = pd.read_sql("SELECT * FROM vendor_mapping", conn)
        edited = st.data_editor(
            mapping_df,
            num_rows="dynamic",
            use_container_width=True
        )

        if st.button("업체 매칭 저장"):
            c.execute("DELETE FROM vendor_mapping")
            for _, row in edited.iterrows():
                c.execute(
                    "INSERT INTO vendor_mapping VALUES (?, ?, ?)",
                    (row["부문"], row["지역팀"], row["업체명"])
                )
            conn.commit()
            st.success("업체 매칭 정보가 저장되었습니다.")
