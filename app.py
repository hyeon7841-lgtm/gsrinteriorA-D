import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, date

st.set_page_config(layout="wide", page_title="집기입고 현황")

DB = "data.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

db = conn()
c = db.cursor()

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
    입고완료 INTEGER DEFAULT 0,
    입고완료일 TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS vendor_mapping (
    부문 TEXT, 지역팀 TEXT, 영업팀 TEXT, 업체명 TEXT
)
""")
db.commit()

# ===============================
# 옵션
# ===============================
부문목록 = [f"{i}부문" for i in range(1, 7)]
지역팀목록 = ["1지역", "2지역", "3지역", "4지역", "신선영업1", "신선영업2"]
영업팀목록 = [f"{i}팀" for i in range(1, 10)]

업체계정 = {
    "한영냉동": "gksdud1!",
    "태민냉동": "xoals1!",
    "우단시스템": "dneks1!"
}

# ===============================
# 세션
# ===============================
if "vendor" not in st.session_state:
    st.session_state.vendor = None
if "admin" not in st.session_state:
    st.session_state.admin = False

# ===============================
# 메뉴
# ===============================
menu = st.sidebar.radio("메뉴", ["집기입고 문의", "입고문의 처리", "데이터 관리"])

# =====================================================
# 1. 집기입고 문의
# =====================================================
if menu == "집기입고 문의":
    st.header("📦 집기입고 문의")

    with st.form("req", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            부문 = st.selectbox("부문", 부문목록)
            지역팀 = st.selectbox("지역팀", 지역팀목록)
            영업팀 = st.selectbox("영업팀", 영업팀목록)
            담당자 = st.text_input("담당자명")
        with c2:
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
                부문, 지역팀, 영업팀, 담당자,
                연락처, 점포명, 요청,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                업체
            ))
            db.commit()
            st.success("등록 완료")
            st.rerun()

    df = pd.read_sql("SELECT * FROM requests ORDER BY id DESC", db)

    st.subheader("🟡 문의접수")
    st.dataframe(df[(df["예정입고일"].isna()) & (df["입고완료"] == 0)], hide_index=True)

    st.subheader("🟠 처리현황")
    st.dataframe(df[(df["예정입고일"].notna()) & (df["입고완료"] == 0)], hide_index=True)

    st.subheader("🟢 입고완료")
    st.dataframe(df[df["입고완료"] == 1], hide_index=True)

# =====================================================
# 2. 입고문의 처리
# =====================================================
if menu == "입고문의 처리":
    st.header("🏭 입고문의 처리")

    if not st.session_state.vendor:
        vid = st.text_input("업체 ID")
        vpw = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            for k, v in 업체계정.items():
                if k.lower() == vid.lower() and v == vpw:
                    st.session_state.vendor = k
                    st.rerun()
            st.error("로그인 실패")
    else:
        st.info(f"로그인 업체 : {st.session_state.vendor}")
        df = pd.read_sql(
            "SELECT * FROM requests WHERE 업체명=? ORDER BY id DESC",
            db,
            params=(st.session_state.vendor,)
        )

        st.dataframe(df, hide_index=True)

        미처리 = df[df["입고완료"] == 0]
        if not 미처리.empty:
            선택 = st.selectbox("처리할 문의 ID", 미처리["id"])
            예정 = st.date_input("예정입고일", date.today())
            완료 = st.checkbox("입고완료")

            if st.button("저장"):
                완료일 = date.today().strftime("%Y-%m-%d") if 완료 else None
                c.execute("""
                UPDATE requests
                SET 예정입고일=?, 입고완료=?, 입고완료일=?
                WHERE id=?
                """, (예정.strftime("%Y-%m-%d"), int(완료), 완료일, 선택))
                db.commit()
                st.success("처리 완료")
                st.rerun()

# =====================================================
# 3. 데이터 관리
# =====================================================
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
        df = pd.read_sql("SELECT * FROM requests", db)

        # ===== 그래프 =====
        total = len(df)
        done = df["입고완료"].sum()
        ing = total - done

        chart_df = pd.DataFrame({
            "구분": ["전체", "처리중", "완료"],
            "건수": [total, ing, done],
            "처리율": [done / total * 100 if total else 0] * 3
        })

        bar = alt.Chart(chart_df).mark_bar().encode(
            x="구분",
            y="건수"
        )

        line = alt.Chart(chart_df).mark_line(color="red").encode(
            x="구분",
            y="처리율"
        )

        st.altair_chart(bar + line, use_container_width=True)

        # ===== 업체 매칭 =====
        st.subheader("🏭 업체 매칭 관리")

        with st.form("map"):
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                b = st.selectbox("부문", 부문목록)
            with m2:
                r = st.selectbox("지역팀", 지역팀목록)
            with m3:
                y = st.selectbox("영업팀", 영업팀목록)
            with m4:
                v = st.text_input("업체명")

            if st.form_submit_button("저장"):
                c.execute("DELETE FROM vendor_mapping WHERE 부문=? AND 지역팀=? AND 영업팀=?", (b, r, y))
                c.execute("INSERT INTO vendor_mapping VALUES (?, ?, ?, ?)", (b, r, y, v))
                c.execute("UPDATE requests SET 업체명=? WHERE 부문=? AND 지역팀=? AND 영업팀=?", (v, b, r, y))
                db.commit()
                st.success("저장 완료")
                st.rerun()

        st.dataframe(pd.read_sql("SELECT * FROM vendor_mapping", db), hide_index=True)
