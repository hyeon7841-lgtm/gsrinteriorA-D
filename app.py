import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="집기입고 관리", layout="wide")

DB_PATH = "data.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_conn()
c = conn.cursor()

# 테이블 생성
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
    입고완료 INTEGER DEFAULT 0
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

menu = st.sidebar.radio(
    "메뉴",
    ["집기입고 문의", "입고문의 처리", "데이터 관리(비밀번호)"]
)

if menu == "집기입고 문의":
    st.header("📦 집기입고 문의")

    with st.form("request_form"):
        부문 = st.text_input("부문")
        지역팀 = st.text_input("지역팀")
        영업팀 = st.text_input("영업팀")
        담당자명 = st.text_input("담당자명")
        연락처 = st.text_input("연락처")
        점포명 = st.text_input("점포명")
        요청집기목록 = st.text_area("요청집기목록")

        submitted = st.form_submit_button("문의 등록")

        if submitted:
            vendor = c.execute(
                "SELECT 업체명 FROM vendor_mapping WHERE 부문=? AND 지역팀=?",
                (부문, 지역팀)
            ).fetchone()

            업체명 = vendor[0] if vendor else "미지정"

            c.execute("""
            INSERT INTO requests
            (부문, 지역팀, 영업팀, 담당자명, 연락처, 점포명, 요청집기목록, 등록일, 업체명)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                부문, 지역팀, 영업팀, 담당자명,
                연락처, 점포명, 요청집기목록,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                업체명
            ))
            conn.commit()
            st.success("입고 문의가 등록되었습니다.")

if menu == "입고문의 처리":
    st.header("📋 집기입고 확인요청 목록")
    df = pd.read_sql("SELECT * FROM requests", conn)
    st.dataframe(df, use_container_width=True)

    req_id = st.number_input("처리할 문의 ID", min_value=1, step=1)
    예정입고일 = st.date_input("예정입고일")
    완료 = st.checkbox("입고완료")

    if st.button("저장"):
        c.execute("""
        UPDATE requests
        SET 예정입고일=?, 입고완료=?
        WHERE id=?
        """, (
            예정입고일.strftime("%Y-%m-%d"),
            int(완료),
            req_id
        ))
        conn.commit()
        st.success("처리 상태가 업데이트되었습니다.")

if menu == "데이터 관리(비밀번호)":
    pw = st.text_input("비밀번호 입력", type="password")

    if pw == "시설":
        st.header("📊 처리 현황")

        df = pd.read_sql("SELECT * FROM requests", conn)
        st.dataframe(df)

        st.subheader("업체 매칭 관리")
        부문 = st.text_input("부문(매칭)")
        지역팀 = st.text_input("지역팀(매칭)")
        업체명 = st.text_input("업체명")

        if st.button("매칭 저장"):
            c.execute("DELETE FROM vendor_mapping WHERE 부문=? AND 지역팀=?", (부문, 지역팀))
            c.execute("INSERT INTO vendor_mapping VALUES (?, ?, ?)", (부문, 지역팀, 업체명))
            conn.commit()
            st.success("매칭 저장 완료")
    else:
        st.warning("비밀번호를 입력하세요")
