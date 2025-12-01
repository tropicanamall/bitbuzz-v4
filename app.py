import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import altair as alt

# --- 1. Page Configuration ---
st.set_page_config(page_title="BITBUZZ Manager v5.0", layout="wide")
st.title("🚀 BITBUZZ Production Manager v5.0")

# --- 2. Google Sheets Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    """Fetch data with error handling"""
    try:
        # ttl=0 to prevent caching old data
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except:
        return pd.DataFrame()

def update_data(worksheet_name, df):
    """Update data safe mode"""
    clean_df = df.fillna("").astype(str)
    conn.update(worksheet=worksheet_name, data=clean_df)

# --- 3. Sidebar: Emergency Fix Button (핵심 기능) ---
with st.sidebar:
    st.header("🔧 System Tools")
    st.info("If you see a red error, click the button below to fix it automatically.")
    
    if st.button("🚨 Fix/Reset Config Tab"):
        # 이 버튼을 누르면 강제로 깨끗한 데이터를 덮어씌웁니다.
        try:
            default_config = pd.DataFrame({
                "employees": ["EJONG", "Manager"],
                "channels": ["Shorts Channel", "Review Channel"]
            })
            update_data("config", default_config)
            st.success("System Repaired! Please refresh the page.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. Load Settings ---
try:
    config_df = get_data("config")
    # 데이터가 비어있거나 깨졌을 경우를 대비
    if config_df.empty or 'employees' not in config_df.columns:
        # 메모리 상에서라도 돌아가게 임시 데이터 생성
        config_df = pd.DataFrame({"employees": ["EJONG"], "channels": ["Channel 1"]})
except:
    config_df = pd.DataFrame({"employees": ["EJONG"], "channels": ["Channel 1"]})

# 리스트 변환
employees_list = config_df['employees'].replace("", pd.NA).dropna().unique().tolist()
channels_list = config_df['channels'].replace("", pd.NA).dropna().unique().tolist()

# --- 5. Load Logs ---
df_logs = get_data("logs")
if not df_logs.empty:
    if "Views" not in df_logs.columns:
        df_logs["Views"] = 0
        update_data("logs", df_logs)

# --- 6. Tabs Layout ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard", 
    "📝 New Entry", 
    "🗂️ Data & Views", 
    "⚙️ Settings" # 설정 탭 부활!
])

# [TAB 1] Dashboard
with tab1:
    st.header("📈 Performance Overview")
    if df_logs.empty:
        st.info("No data available yet.")
    else:
        df_logs['Date'] = pd.to_datetime(df_logs['Date'], errors='coerce')
        curr_y, curr_m = datetime.now().year, datetime.now().month
        this_month = df_logs[(df_logs['Date'].dt.year == curr_y) & (df_logs['Date'].dt.month == curr_m)]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Videos (This Month)", len(this_month))
        c2.metric("Active Creators", this_month['Staff'].nunique())
        
        views_numeric = pd.to_numeric(this_month['Views'], errors='coerce').fillna(0)
        c3.metric("Total Views", f"{int(views_numeric.sum()):,}")
        st.divider()

        g1, g2 = st.columns(2)
        with g1:
            st.subheader("🏆 Top Creators")
            if not this_month.empty:
                cnt = this_month['Staff'].value_counts().reset_index()
                cnt.columns = ['Staff', 'Count']
                st.altair_chart(alt.Chart(cnt).mark_bar().encode(x=alt.X('Staff', sort='-y'), y='Count', color='Staff'), use_container_width=True)
        with g2:
            st.subheader("📅 Monthly Trend")
            if not df_logs.empty:
                trend = df_logs.groupby(df_logs['Date'].dt.to_period('M')).size().reset_index(name='Count')
                trend['Date'] = trend['Date'].astype(str)
                st.altair_chart(alt.Chart(trend).mark_line(point=True).encode(x='Date', y='Count'), use_container_width=True)

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
                try:
                    old_df = get_data("logs")
                    new_row = pd.DataFrame([{
                        "Date": str(d), "Staff": n, "Channel": ch, "Title": t, "Link": l, 
                        "Views": "0", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    final_df = pd.concat([old_df, new_row], ignore_index=True)
                    update_data("logs", final_df)
                    st.success("Saved!"); st.rerun()
                except Exception as e:
                    st.error(f"Save failed. Please click 'Fix Config' button in sidebar. Error: {e}")
            else: st.error("Title required.")

# [TAB 3] Data & Views
with tab3:
    if st.button("Refresh Data"): st.rerun()
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

# [TAB 4] Settings (관리자 기능 부활)
with tab4:
    st.info("Manage your Staff and Channels here.")
    c1, c2 = st.columns(2)
    with c1:
        st.write("#### 👤 Staff List")
        st.write(", ".join(employees_list))
        new_emp = st.text_input("Add Staff", key="emp")
        if st.button("Add Staff"):
            employees_list.append(new_emp)
            # 길이 맞추기 및 저장
            max_len = max(len(employees_list), len(channels_list))
            e_series = pd.Series(employees_list + [""]*(max_len-len(employees_list)))
            c_series = pd.Series(channels_list + [""]*(max_len-len(channels_list)))
            
            try:
                new_config = pd.DataFrame({"employees": e_series, "channels": c_series})
                update_data("config", new_config)
                st.rerun()
            except:
                st.error("Error! Please click the 'Fix/Reset' button on the left sidebar.")
            
    with c2:
        st.write("#### 📺 Channel List")
        st.write(", ".join(channels_list))
        new_ch = st.text_input("Add Channel", key="ch")
        if st.button("Add Channel"):
            channels_list.append(new_ch)
            # 길이 맞추기 및 저장
            max_len = max(len(employees_list), len(channels_list))
            e_series = pd.Series(employees_list + [""]*(max_len-len(employees_list)))
            c_series = pd.Series(channels_list + [""]*(max_len-len(channels_list)))
            
            try:
                new_config = pd.DataFrame({"employees": e_series, "channels": c_series})
                update_data("config", new_config)
                st.rerun()
            except:
                st.error("Error! Please click the 'Fix/Reset' button on the left sidebar.")
