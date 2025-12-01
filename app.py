import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import altair as alt

# --- 1. Page Configuration ---
st.set_page_config(page_title="BITBUZZ Production Manager", layout="wide")
st.title("🚀 BITBUZZ Production Manager v4.6")

# --- 2. Google Sheets Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except:
        return pd.DataFrame()

def update_data(worksheet_name, df):
    # 데이터를 문자로 변환하여 저장
    clean_df = df.fillna("").astype(str)
    try:
        conn.update(worksheet=worksheet_name, data=clean_df)
    except Exception as e:
        # 에러가 나면 화면에 경고 표시
        st.error(f"⚠️ 저장 실패! 구글 시트 '{worksheet_name}' 탭에 빈 행(Rows)이 너무 많습니다. 2행부터 끝까지 삭제해주세요.")
        st.stop() # 프로그램 중단 방지

# --- 3. Load Settings ---
try:
    config_df = get_data("config")
    # 엑셀이 비어있으면 초기값 생성
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
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📝 New Entry", "🗂️ Data & Views", "⚙️ Settings"])

# [TAB 1] Dashboard
with tab1:
    st.header("📈 Monthly Performance")
    if df_logs.empty:
        st.info("No data.")
    else:
        df_logs['Date'] = pd.to_datetime(df_logs['Date'], errors='coerce')
        curr_y, curr_m = datetime.now().year, datetime.now().month
        this_month = df_logs[(df_logs['Date'].dt.year == curr_y) & (df_logs['Date'].dt.month == curr_m)]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Videos (Month)", len(this_month))
        c2.metric("Creators", this_month['Staff'].nunique())
        c3.metric("Views", f"{int(pd.to_numeric(this_month['Views'], errors='coerce').fillna(0).sum()):,}")
        st.divider()
        
        g1, g2 = st.columns(2)
        with g1:
            if not this_month.empty:
                cnt = this_month['Staff'].value_counts().reset_index()
                cnt.columns = ['Staff', 'Count']
                st.altair_chart(alt.Chart(cnt).mark_bar().encode(x=alt.X('Staff', sort='-y'), y='Count', color='Staff'), use_container_width=True)
        with g2:
            if not df_logs.empty:
                trend = df_logs.groupby(df_logs['Date'].dt.to_period('M')).size().reset_index(name='Count')
                trend['Date'] = trend['Date'].astype(str)
                st.altair_chart(alt.Chart(trend).mark_line(point=True).encode(x='Date', y='Count'), use_container_width=True)

# [TAB 2] New Entry
with tab2:
    st.subheader("Submit Work")
    with st.form("entry"):
        c1, c2 = st.columns(2)
        d = c1.date_input("Date")
        n = c1.selectbox("Name", employees_list)
        ch = c2.selectbox("Channel", channels_list)
        t = st.text_input("Title")
        l = st.text_input("Link")
        if st.form_submit_button("Submit"):
            if t:
                new = pd.DataFrame([{"Date": str(d), "Staff": n, "Channel": ch, "Title": t, "Link": l, "Views": "0", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                update_data("logs", pd.concat([get_data("logs"), new], ignore_index=True))
                st.success("Saved!"); st.rerun()
            else: st.error("Title required.")

# [TAB 3] Data
with tab3:
    if st.button("Refresh"): st.rerun()
    edited = st.data_editor(get_data("logs"), num_rows="dynamic", use_container_width=True, hide_index=True, column_config={"Link": st.column_config.LinkColumn("Link")})
    if st.button("Save Changes"):
        update_data("logs", edited)
        st.success("Updated!")

# [TAB 4] Settings
with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.write("#### Staff"); st.write(", ".join(employees_list))
        new_emp = st.text_input("New Staff", key="ne")
        if st.button("Add Staff"):
            employees_list.append(new_emp)
            # 안전한 저장 로직
            max_len = max(len(employees_list), len(channels_list))
            e = pd.Series(employees_list + [""]*(max_len-len(employees_list)))
            c = pd.Series(channels_list + [""]*(max_len-len(channels_list)))
            update_data("config", pd.DataFrame({"employees": e, "channels": c}))
            st.rerun()
    with c2:
        st.write("#### Channel"); st.write(", ".join(channels_list))
        new_ch = st.text_input("New Channel", key="nc")
        if st.button("Add Channel"):
            channels_list.append(new_ch)
            # 안전한 저장 로직
            max_len = max(len(employees_list), len(channels_list))
            e = pd.Series(employees_list + [""]*(max_len-len(employees_list)))
            c = pd.Series(channels_list + [""]*(max_len-len(channels_list)))
            update_data("config", pd.DataFrame({"employees": e, "channels": c}))
            st.rerun()
