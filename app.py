import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="집기입고 현황", layout="wide")

DB = "data.db"

def conn_db():
    return sqlite3.connect(DB, check_same_thread=False)

conn = conn_db()
c = conn.cursor()

# ==============================
# 테이블
# ==============================
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
conn.commit()

# ==============================
# 옵션
# ==============================
부문목록 = [f"{i}부문" for i in range(1,7)]
지역팀목록 = ["1지역","2지역","3지역","4지역","신선영업1","신선영업2"]
영업팀목록 = [f"{i}팀" for i in range(1,10)]

업체계정 = {
    "한영냉동": "한영1!",
    "태민냉동": "태민1!",
    "우단시스템": "우단시스템1!"
}

if "vendor" not in st.session_state:
    st.session_state.vendor = None

menu = st.sidebar.radio("메뉴", ["집기입고 문의","입고문의 처리"])

# ==============================
# 1️⃣ 집기입고 문의 (방문자 공개)
# ==============================
if menu == "집기입고 문의":
    st.header("📦 집기입고 문의 현황")

    with st.form("req"):
        col1,col2,col3 = st.columns(3)
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

            c.execute("""
            INSERT INTO requests
            (부문,지역팀,영업팀,담당자명,연락처,점포명,
             요청집기목록,등록일,상태)
            VALUES (?,?,?,?,?,?,?,?, '접수')
            """,(
                부문,지역팀,영업팀,
                담당자명,연락처,점포명,
                요청집기목록,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
            conn.commit()
            st.success("문의가 접수되었습니다.")
            st.rerun()

    # 🔍 검색 필터
    st.divider()
    search = st.text_input("🔍 점포명 검색")

    df = pd.read_sql("SELECT * FROM requests ORDER BY id DESC", conn)
    if search:
        df = df[df["점포명"].str.contains(search, case=False, na=False)]

    colA, colB, colC = st.columns(3)

    colA.subheader("🔵 접수")
    colA.dataframe(df[df["상태"]=="접수"], hide_index=True)

    colB.subheader("🟡 처리현황")
    colB.dataframe(df[df["상태"]=="처리중"], hide_index=True)

    colC.subheader("🟢 입고완료")
    colC.dataframe(df[df["상태"]=="완료"], hide_index=True)

# ==============================
# 2️⃣ 입고문의 처리 (업체)
# ==============================
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
            "SELECT * FROM requests WHERE 상태!='완료' ORDER BY id DESC",
            conn
        )

        st.subheader("📋 처리 대상 문의")
        st.dataframe(df, hide_index=True)

        if not df.empty:
            선택ID = st.selectbox("문의 선택 (ID)", df["id"])
            예정일 = st.date_input("입고예정일", date.today())
            완료 = st.checkbox("입고완료 처리")

            if st.button("처리 저장"):
                상태 = "완료" if 완료 else "처리중"
                c.execute(
                    "UPDATE requests SET 예정입고일=?, 상태=? WHERE id=?",
                    (예정일.strftime("%Y-%m-%d"), 상태, 선택ID)
                )
                conn.commit()
                st.success("처리되었습니다.")
                st.rerun()
