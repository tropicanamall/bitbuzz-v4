import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import altair as alt

# --- 1. Page Configuration ---
st.set_page_config(page_title="BITBUZZ Production Manager", layout="wide")
st.title("🚀 BITBUZZ Production Manager v4.3")

# --- 2. Google Sheets Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    """Fetch data safe mode"""
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except:
        return pd.DataFrame()

def update_data(worksheet_name, df):
    """Update data safe mode"""
    # 모든 데이터를 강제로 문자열로 변환하고, 빈 값은 빈칸("")으로 처리
    clean_df = df.fillna("").astype(str)
    conn.update(worksheet=worksheet_name, data=clean_df)

# --- 3. Load Settings (Staff/Channels) ---
# config 탭이 비어있거나 에러가 나도 기본값으로 시작하게 안전장치 추가
try:
    config_df = get_data("config")
    # 데이터가 아예 없거나 헤더만 있을 경우
    if config_df.empty or 'employees' not in config_df.columns:
        # 엑셀이 비어있으면 이 기본값으로 시작합니다
        config_df = pd.DataFrame({
            "employees": ["EJONG", "Manager"], 
            "channels": ["Shorts Channel", "Review Channel"]
        })
        # 여기서 엑셀에 한번 쏴줍니다 (초기화)
        update_data("config", config_df)
except:
    # 최악의 경우(엑셀 연결 실패 등) 메모리에서라도 돌아가게 함
    config_df = pd.DataFrame({"employees": [], "channels": []})

# 리스트 변환 (빈칸 제거)
employees_list = config_df['employees'].replace("", pd.NA).dropna().unique().tolist()
channels_list = config_df['channels'].replace("", pd.NA).dropna().unique().tolist()

# --- 4. Load Logs ---
df_logs = get_data("logs")
if not df_logs.empty:
    if "Views" not in df_logs.columns:
        df_logs["Views"] = 0
        update_data("logs", df_logs)

# --- 5. Tabs Layout ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard", 
    "📝 New Entry", 
    "🗂️ Data & Views", 
    "⚙️ Settings"
])

# [TAB 1] Dashboard
with tab1:
    st.header("📈 Monthly Performance Overview")
    if df_logs.empty:
        st.info("No data available yet.")
    else:
        df_logs['Date'] = pd.to_datetime(df_logs['Date'], errors='coerce')
        current_year = datetime.now().year
        current_month = datetime.now().month
        this_month_df = df_logs[
            (df_logs['Date'].dt.year == current_year) & 
            (df_logs['Date'].dt.month == current_month)
        ]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Videos (This Month)", len(this_month_df))
        c2.metric("Active Creators", this_month_df['Staff'].nunique())
        
        # 조회수 에러 방지 (숫자로 강제 변환)
        views_numeric = pd.to_numeric(this_month_df['Views'], errors='coerce').fillna(0)
        c3.metric("Total Views", f"{int(views_numeric.sum()):,}")
        st.divider()

        g1, g2 = st.columns(2)
        with g1:
            st.subheader("🏆 Top Performers")
            if not this_month_df.empty:
                emp_counts = this_month_df['Staff'].value_counts().reset_index()
                emp_counts.columns = ['Staff', 'Count']
                chart = alt.Chart(emp_counts).mark_bar().encode(
                    x=alt.X('Staff', sort='-y'), y='Count', color='Staff', tooltip=['Staff', 'Count']
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)
        with g2:
            st.subheader("📅 Monthly Trend")
            if not df_logs.empty:
                monthly = df_logs.groupby(df_logs['Date'].dt.to_period('M')).size().reset_index(name='Count')
                monthly['Date'] = monthly['Date'].astype(str)
                line = alt.Chart(monthly).mark_line(point=True).encode(
                    x='Date', y='Count', tooltip=['Date', 'Count']
                ).properties(height=300)
                st.altair_chart(line, use_container_width=True)

# [TAB 2] New Entry
with tab2:
    st.subheader("Submit Daily Work")
    with st.form("entry"):
        c1, c2 = st.columns(2)
        d = c1.date_input("Date")
        n = c1.selectbox("Name", employees_list)
        ch = c2.selectbox("Channel", channels_list)
        t = st.text_input("Title")
        l = st.text_input("Link")
        if st.form_submit_button("Submit"):
            if t:
                old_df = get_data("logs")
                new_row = pd.DataFrame([{
                    "Date": str(d), "Staff": n, "Channel": ch, "Title": t, "Link": l, 
                    "Views": "0", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                final_df = pd.concat([old_df, new_row], ignore_index=True)
                update_data("logs", final_df)
                st.success("Saved!"); st.rerun()
            else: st.error("Title required.")

# [TAB 3] Data & Views
with tab3:
    st.warning("Double-click 'Views' to edit.")
    if st.button("Refresh"): st.rerun()
    cur_df = get_data("logs")
    if not cur_df.empty:
        cur_df = cur_df.sort_values(by="Date", ascending=False)
        edited = st.data_editor(
            cur_df, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={"Link": st.column_config.LinkColumn("Link")}
        )
        if st.button("Save Changes"):
            update_data("logs", edited)
            st.success("Updated!")
    else: st.write("No data.")

# [TAB 4] Settings
with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.write("#### Staff List")
        st.write(", ".join(employees_list))
        new_emp = st.text_input("Add Staff", key="emp")
        if st.button("Add"):
            employees_list.append(new_emp)
            max_len = max(len(employees_list), len(channels_list))
            e_series = pd.Series(employees_list + [""]*(max_len-len(employees_list)))
            c_series = pd.Series(channels_list + [""]*(max_len-len(channels_list)))
            
            # v4.3 핵심 수정: 안전하게 데이터프레임 생성
            new_config = pd.DataFrame({"employees": e_series, "channels": c_series})
            update_data("config", new_config)
            st.rerun()
            
    with c2:
        st.write("#### Channel List")
        st.write(", ".join(channels_list))
        new_ch = st.text_input("Add Channel", key="ch")
        if st.button("Add "):
            channels_list.append(new_ch)
            max_len = max(len(employees_list), len(channels_list))
            e_series = pd.Series(employees_list + [""]*(max_len-len(employees_list)))
            c_series = pd.Series(channels_list + [""]*(max_len-len(channels_list)))
            
            # v4.3 핵심 수정: 안전하게 데이터프레임 생성
            new_config = pd.DataFrame({"employees": e_series, "channels": c_series})
            update_data("config", new_config)
            st.rerun()
    
