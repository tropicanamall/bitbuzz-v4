import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import altair as alt

# --- 1. Page Configuration ---
st.set_page_config(page_title="BITBUZZ Manager v5.1", layout="wide")
st.title("🚀 BITBUZZ Production Manager v5.1")

# --- 2. Google Sheets Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except:
        return pd.DataFrame()

def update_data(worksheet_name, df):
    # 모든 데이터를 문자열로 변환 (에러 방지)
    clean_df = df.fillna("").astype(str)
    conn.update(worksheet=worksheet_name, data=clean_df)

# 설정 저장 도우미 함수 (추가/삭제 시 사용)
def save_config(emp_list, ch_list):
    # 1. 두 리스트의 길이를 맞춥니다 (짧은 쪽에 빈칸 채우기)
    max_len = max(len(emp_list), len(ch_list))
    
    # 리스트가 비어있을 경우를 대비
    if max_len == 0:
        emp_series = []
        ch_series = []
    else:
        emp_series = emp_list + [""] * (max_len - len(emp_list))
        ch_series = ch_list + [""] * (max_len - len(ch_list))
    
    # 2. 데이터프레임 생성
    new_config = pd.DataFrame({
        "employees": emp_series,
        "channels": ch_series
    })
    
    # 3. 저장
    update_data("config", new_config)

# --- 3. Sidebar: Fix Button ---
with st.sidebar:
    st.header("🔧 System Tools")
    if st.button("🚨 Fix/Reset Config"):
        try:
            default_config = pd.DataFrame({
                "employees": ["EJONG", "Manager"],
                "channels": ["Shorts Channel"]
            })
            update_data("config", default_config)
            st.success("System Repaired! Refresh the page.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. Load Settings ---
try:
    config_df = get_data("config")
    if config_df.empty or 'employees' not in config_df.columns:
        config_df = pd.DataFrame({"employees": ["EJONG"], "channels": ["Channel 1"]})
except:
    config_df = pd.DataFrame({"employees": ["EJONG"], "channels": ["Channel 1"]})

# 리스트 변환 (빈칸 제거)
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
    "⚙️ Settings"
])

# [TAB 1] Dashboard
with tab1:
    st.header("📈 Performance Overview")
    if df_logs.empty:
        st.info("No data yet.")
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
                    st.error(f"Error: {e}")
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

# [TAB 4] Settings (삭제 기능 포함)
with tab4:
    st.info("Manage your Staff and Channels here. (Add / Delete)")
    
    col_staff, col_channel = st.columns(2)
    
    # 1. 직원 관리 섹션
    with col_staff:
        st.markdown("### 👤 Staff Management")
        st.write(f"**Current List:** {', '.join(employees_list)}")
        
        # 추가
        with st.expander("➕ Add Staff", expanded=True):
            new_emp = st.text_input("Name", key="add_emp_input")
            if st.button("Add Staff"):
                if new_emp and new_emp not in employees_list:
                    employees_list.append(new_emp)
                    save_config(employees_list, channels_list)
                    st.success("Added!")
                    st.rerun()
                elif new_emp in employees_list:
                    st.warning("Already exists.")

        # 삭제 (선택박스로 안전하게)
        with st.expander("🗑️ Delete Staff"):
            del_emp = st.selectbox("Select to remove", ["Select..."] + employees_list, key="del_emp_select")
            if st.button("Delete Staff"):
                if del_emp != "Select...":
                    employees_list.remove(del_emp)
                    save_config(employees_list, channels_list)
                    st.success(f"Removed {del_emp}")
                    st.rerun()

    # 2. 채널 관리 섹션
    with col_channel:
        st.markdown("### 📺 Channel Management")
        st.write(f"**Current List:** {', '.join(channels_list)}")
        
        # 추가
        with st.expander("➕ Add Channel", expanded=True):
            new_ch = st.text_input("Channel Name", key="add_ch_input")
            if st.button("Add Channel"):
                if new_ch and new_ch not in channels_list:
                    channels_list.append(new_ch)
                    save_config(employees_list, channels_list)
                    st.success("Added!")
                    st.rerun()
                elif new_ch in channels_list:
                    st.warning("Already exists.")

        # 삭제
        with st.expander("🗑️ Delete Channel"):
            del_ch = st.selectbox("Select to remove", ["Select..."] + channels_list, key="del_ch_select")
            if st.button("Delete Channel"):
                if del_ch != "Select...":
                    channels_list.remove(del_ch)
                    save_config(employees_list, channels_list)
                    st.success(f"Removed {del_ch}")
                    st.rerun()
