import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import altair as alt

# --- 1. Page Configuration ---
st.set_page_config(page_title="BITBUZZ Production Manager", layout="wide")
st.title("🚀 BITBUZZ Production Manager v4.5")

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
    """Update data with Auto-Repair (Clear & Write)"""
    # 데이터 정리 (빈칸, 문자열 변환)
    clean_df = df.fillna("").astype(str)
    
    try:
        # 1차 시도: 그냥 저장
        conn.update(worksheet=worksheet_name, data=clean_df)
    except Exception:
        # 2차 시도 (에러 발생 시): 시트를 싹 지우고 다시 씀 (가장 확실한 방법)
        try:
            # 구글 시트를 직접 엽니다
            sh = conn.client.open_by_url(conn.spreadsheet)
            ws = sh.worksheet(worksheet_name)
            
            # 내용을 전부 지웁니다 (Clear)
            ws.clear()
            
            # 다시 씁니다
            conn.update(worksheet=worksheet_name, data=clean_df)
        except Exception as e:
            # 그래도 안되면 메시지 출력
            st.error(f"저장 오류: {e}")

# --- 3. Load Settings (Staff/Channels) ---
try:
    config_df = get_data("config")
    # 데이터가 없으면 기본값으로 초기화
    if config_df.empty or 'employees' not in config_df.columns:
        config_df = pd.DataFrame({
            "employees": ["EJONG", "Manager"], 
            "channels": ["Shorts Channel", "Review Channel"]
        })
        update_data("config", config_df)
except:
    config_df = pd.DataFrame({"employees": [], "channels": []})

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
            new_config = pd.DataFrame({"employees": e_series, "channels": c_series})
            update_data("config", new_config)
            st.rerun()
