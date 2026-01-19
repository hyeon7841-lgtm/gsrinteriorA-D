import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, date

st.set_page_config(layout="wide", page_title="집기입고 관리")

DB = "data.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

c = conn().cursor()

# ===============================
# 테이블
# ===============================
c.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    부문 TEXT, 지역팀 TEXT, 영업팀 TEXT,
    담당자명 TEXT, 연락처 TEXT, 점포명 TEXT,
    요청집기목록 TEXT,
    등록일 TEXT,
    업체명 TEXT,
    예정입고일 TEXT,
    상태 TEXT DEFAULT '접수'
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS completed_archive (
    * FROM requests
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS vendor_mapping (
    부문 TEXT, 지역팀 TEXT, 영업팀 TEXT, 업체명 TEXT
)
""")

conn().commit()

# ===============================
# 옵션
# ===============================
부문목록 = [f"{i}부문" for i in range(1, 7)]
지역팀목록 = ["1지역", "2지역", "3지역", "4지역", "신선영업1", "신선영업2"]
영업팀목록 = [f"{i}팀" for i in range(1, 10)]

업체계정 = {
    "한영냉동": "한영1!",
    "태민냉동": "태민1!",
    "우단시스템": "우단시스템1!"
}

# ===============================
# 세션
# ===============================
if "vendor" not in st.session_state:
    st.session_state.vendor = None
if "admin" not in st.session_state:
    st.session_state.admin = False

menu = st.sidebar.radio("메뉴", ["집기입고 문의", "입고문의 처리", "데이터 관리"])

if menu != "입고문의 처리":
    st.session_state.vendor = None
if menu != "데이터 관리":
    st.session_state.admin = False

# ==================================================
# 1. 집기입고 문의
# ==================================================
if menu == "집기입고 문의":
    st.header("📦 집기입고 문의")

    with st.form("req"):
        부문 = st.selectbox("부문", 부문목록)
        지역팀 = st.selectbox("지역팀", 지역팀목록)
        영업팀 = st.selectbox("영업팀", 영업팀목록)
        담당자 = st.text_input("담당자명")
        연락처 = st.text_input("연락처(-없이)")
        점포명 = st.text_input("점포명")
        요청 = st.text_area("요청집기목록")

        if st.form_submit_button("등록"):
            연락처 = 연락처.replace("-", "")
            if 점포명.endswith("점"):
                점포명 = 점포명[:-1]

            v = c.execute(
                "SELECT 업체명 FROM vendor_mapping WHERE 부문=? AND 지역팀=? AND 영업팀=?",
                (부문, 지역팀, 영업팀)
            ).fetchone()
            업체 = v[0] if v else "미지정"

            c.execute("""
            INSERT INTO requests
            (부문, 지역팀, 영업팀, 담당자명, 연락처, 점포명,
             요청집기목록, 등록일, 업체명)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                부문, 지역팀, 영업팀, 담당자, 연락처,
                점포명, 요청, datetime.now().strftime("%Y-%m-%d %H:%M"),
                업체
            ))
            conn().commit()
            st.success("등록 완료")
            st.rerun()

    df = pd.read_sql("SELECT * FROM requests", conn())
    st.subheader("📋 전체 현황")
    st.dataframe(df, hide_index=True)

# ==================================================
# 2. 입고문의 처리
# ==================================================
if menu == "입고문의 처리":
    st.header("🏭 입고문의 처리")

    if not st.session_state.vendor:
        vid = st.text_input("업체 ID")
        pw = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            for k, v in 업체계정.items():
                if k.lower() == vid.lower() and pw == v:
                    st.session_state.vendor = k
                    st.rerun()
            st.error("로그인 실패")
    else:
        df = pd.read_sql(
            "SELECT * FROM requests WHERE 업체명=?",
            conn(), params=(st.session_state.vendor,)
        )

        st.dataframe(
            df.style.apply(
                lambda r: ["background:#ffe6e6"] * len(r) if r["상태"] == "접수" else [""],
                axis=1
            ),
            hide_index=True
        )

        선택 = st.selectbox("처리할 ID", df["id"])
        예정 = st.date_input("입고예정일", date.today())
        완료 = st.checkbox("입고완료")

        if st.button("저장"):
            상태 = "완료" if 완료 else "처리중"
            c.execute("""
            UPDATE requests SET 예정입고일=?, 상태=?
            WHERE id=?
            """, (예정.strftime("%Y-%m-%d"), 상태, 선택))
            conn().commit()
            st.success("처리 완료")
            st.rerun()

# ==================================================
# 3. 데이터 관리
# ==================================================
if menu == "데이터 관리":
    st.header("📊 데이터 관리")

    if not st.session_state.admin:
        pw = st.text_input("비밀번호", type="password")
        if st.button("확인"):
            if pw in ["시설", "tltjf"]:
                st.session_state.admin = True
                st.rerun()
            else:
                st.error("비밀번호 오류")
    else:
        df = pd.read_sql("SELECT * FROM requests", conn())

        # ===== 그래프 함수 =====
        def draw_chart(group):
            g = df.groupby(group).agg(
                전체=("id", "count"),
                완료=("상태", lambda x: (x == "완료").sum())
            ).reset_index()
            g["처리율"] = g["완료"] / g["전체"] * 100

            bar = alt.Chart(g).mark_bar().encode(
                x=group, y="전체"
            )
            line = alt.Chart(g).mark_line(color="red").encode(
                x=group, y=alt.Y("처리율", axis=alt.Axis(title="처리율(%)"))
            )

            st.altair_chart(
                alt.layer(bar, line).resolve_scale(y="independent"),
                use_container_width=True
            )

        st.subheader("업체별 처리현황")
        draw_chart("업체명")

        st.subheader("부문별 처리현황")
        draw_chart("부문")

        st.subheader("부문-지역팀 처리현황")
        df["부문지역"] = df["부문"] + "-" + df["지역팀"]
        draw_chart("부문지역")

        # ===== 완료보관함 이동 =====
        st.subheader("📦 완료보관함 이동")
        if st.button("입고완료 → 완료보관함"):
            c.execute("""
            INSERT INTO completed_archive SELECT * FROM requests WHERE 상태='완료'
            """)
            c.execute("DELETE FROM requests WHERE 상태='완료'")
            conn().commit()
            st.success("이동 완료")
            st.rerun()

        # ===== 완료보관함 초기화 =====
        pw = st.text_input("완료보관함 초기화 비밀번호", type="password")
        if st.button("완료보관함 초기화"):
            if pw == "이현호":
                c.execute("DELETE FROM completed_archive")
                conn().commit()
                st.success("완전 삭제 완료")
            else:
                st.error("비밀번호 오류")

        # ===== 잘못 접수 삭제 =====
        st.subheader("❌ 잘못 접수된 문의 삭제")
        del_id = st.selectbox("삭제할 문의 ID", df["id"])
        if st.button("삭제"):
            c.execute("DELETE FROM requests WHERE id=?", (del_id,))
            conn().commit()
            st.success("삭제 완료")
            st.rerun()
