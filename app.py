import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import altair as alt

# --- 1. 기본 설정 ---
st.set_page_config(page_title="BITBUZZ Manager", layout="wide")
st.title("🚀 BITBUZZ Production Manager v4.7 (비상 모드)")

# --- 2. 구글 시트 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except:
        return pd.DataFrame()

def update_data(worksheet_name, df):
    # 에러가 나도 무시하고 저장 시도
    clean_df = df.fillna("").astype(str)
    try:
        conn.update(worksheet=worksheet_name, data=clean_df)
    except Exception as e:
        st.error(f"저장 중 경고: 엑셀 시트의 빈 행을 정리해주세요. (내용은 저장되지 않았을 수 있습니다.) 에러: {e}")

# --- 3. 설정 (여기가 핵심!) ---
# 엑셀 config 탭을 읽지 않고, 코드로 고정해버립니다. (에러 원천 차단)
employees_list = ["EJONG", "Manager", "Staff1", "Staff2"]
channels_list = ["Shorts Channel", "Review Channel", "Daily Vlog"]

# --- 4. 기록 불러오기 ---
df_logs = get_data("logs")
if not df_logs.empty and "Views" not in df_logs.columns:
    df_logs["Views"] = 0

# --- 5. 화면 구성 ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📝 New Entry", "🗂️ Data List"])

# [탭 1] 대시보드
with tab1:
    st.header("📈 성과 요약")
    if df_logs.empty:
        st.info("데이터가 없습니다.")
    else:
        df_logs['Date'] = pd.to_datetime(df_logs['Date'], errors='coerce')
        # 이번달 필터
        this_month = df_logs[df_logs['Date'].dt.month == datetime.now().month]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("이번달 영상", len(this_month))
        c2.metric("참여 직원", this_month['Staff'].nunique())
        # 조회수 합계
        views = pd.to_numeric(this_month['Views'], errors='coerce').fillna(0).sum()
        c3.metric("총 조회수", f"{int(views):,}")

# [탭 2] 작업 등록
with tab2:
    st.subheader("일일 업무 등록")
    with st.form("entry"):
        c1, c2 = st.columns(2)
        d = c1.date_input("날짜")
        n = c1.selectbox("이름", employees_list)
        ch = c2.selectbox("채널", channels_list)
        t = st.text_input("제목")
        l = st.text_input("링크")
        
        if st.form_submit_button("등록하기"):
            if t:
                new_row = pd.DataFrame([{
                    "Date": str(d), "Staff": n, "Channel": ch, "Title": t, "Link": l, 
                    "Views": "0", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                # 기존 데이터에 합치기
                updated_df = pd.concat([get_data("logs"), new_row], ignore_index=True)
                update_data("logs", updated_df)
                st.success("저장되었습니다!")
                st.rerun()
            else:
                st.error("제목을 입력해주세요.")

# [탭 3] 전체 데이터
with tab3:
    if st.button("새로고침"): st.rerun()
    st.dataframe(get_data("logs"), use_container_width=True)
