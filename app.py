import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import altair as alt

# --- 1. Page Configuration ---
st.set_page_config(page_title="BITBUZZ Production Manager", layout="wide")
st.title("🚀 BITBUZZ Production Manager v4.0")

# --- 2. Google Sheets Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    """Fetch data from Google Sheets"""
    try:
        # ttl=0 ensures we always get fresh data
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except Exception:
        return pd.DataFrame()

def update_data(worksheet_name, df):
    """Update data to Google Sheets"""
    conn.update(worksheet=worksheet_name, data=df)

# --- 3. Load Settings (Staff/Channels) ---
try:
    config_df = get_data("config")
    if config_df.empty or 'employees' not in config_df.columns:
        # Default settings if empty
        config_df = pd.DataFrame({
            "employees": ["Kim", "Lee", "Park"], 
            "channels": ["Shorts Mentor", "That Goal", "K-Beauty"]
        })
        update_data("config", config_df)
except:
    config_df = pd.DataFrame({"employees": [], "channels": []})

# Convert to list after removing empty values
employees_list = config_df['employees'].dropna().unique().tolist()
channels_list = config_df['channels'].dropna().unique().tolist()

# --- 4. Load & Preprocess Logs ---
df_logs = get_data("logs")

# Ensure 'Views' column exists
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

# ==========================================
# [TAB 1] Dashboard (Overview)
# ==========================================
with tab1:
    st.header("📈 Monthly Performance Overview")
    
    if df_logs.empty:
        st.info("No data available yet. Please add entries in the 'New Entry' tab.")
    else:
        # Convert Date column to datetime objects
        df_logs['Date'] = pd.to_datetime(df_logs['Date'])
        
        # Filter for Current Month
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        this_month_df = df_logs[
            (df_logs['Date'].dt.year == current_year) & 
            (df_logs['Date'].dt.month == current_month)
        ]
        
        # Metrics
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("📅 Total Videos (This Month)", f"{len(this_month_df)}")
        col_m2.metric("👥 Active Creators", f"{this_month_df['Staff'].nunique()}")
        
        total_views = this_month_df['Views'].sum() if 'Views' in this_month_df.columns else 0
        col_m3.metric("👀 Total Views (This Month)", f"{total_views:,}")
        
        st.divider()

        # Graphs
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("🏆 Top Performers (This Month)")
            if not this_month_df.empty:
                emp_counts = this_month_df['Staff'].value_counts().reset_index()
                emp_counts.columns = ['Staff', 'Count']
                
                chart = alt.Chart(emp_counts).mark_bar().encode(
                    x=alt.X('Staff', sort='-y'),
                    y='Count',
                    color='Staff',
                    tooltip=['Staff', 'Count']
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.write("No data for this month.")

        with col_g2:
            st.subheader("📅 Monthly Trend (Last 3 Months)")
            # Group by Month
            monthly_trend = df_logs.groupby(df_logs['Date'].dt.to_period('M')).size().reset_index(name='Count')
            monthly_trend['Date'] = monthly_trend['Date'].astype(str)
            
            line_chart = alt.Chart(monthly_trend).mark_line(point=True).encode(
                x='Date',
                y='Count',
                tooltip=['Date', 'Count']
            ).properties(height=300)
            st.altair_chart(line_chart, use_container_width=True)

# ==========================================
# [TAB 2] New Entry (Input)
# ==========================================
with tab2:
    st.subheader("Submit Daily Work")
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        input_date = c1.date_input("Date")
        input_name = c1.selectbox("Creator Name", employees_list)
        input_channel = c2.selectbox("Channel", channels_list)
        
        input_title = st.text_input("Video Title")
        input_url = st.text_input("YouTube Link (URL)")
        
        if st.form_submit_button("Submit"):
            if input_title:
                current_data = get_data("logs")
                
                new_row = pd.DataFrame([{
                    "Date": str(input_date),
                    "Staff": input_name,
                    "Channel": input_channel,
                    "Title": input_title,
                    "Link": input_url,
                    "Views": 0,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                
                updated_logs = pd.concat([current_data, new_row], ignore_index=True)
                update_data("logs", updated_logs)
                st.success("Successfully Saved! Check the Dashboard.")
                st.rerun()
            else:
                st.error("Please enter the Video Title.")

# ==========================================
# [TAB 3] Data & Views (Edit)
# ==========================================
with tab3:
    st.warning("💡 Double-click the 'Views' cell to update view counts. Click 'Save Changes' to apply.")
    
    if st.button("🔄 Refresh Data"):
        st.rerun()

    current_df = get_data("logs")
    
    if not current_df.empty:
        current_df = current_df.sort_values(by="Date", ascending=False)

        edited_df = st.data_editor(
            current_df,
            num_rows="dynamic",
            column_config={
                "Link": st.column_config.LinkColumn("Link"),
                "Views": st.column_config.NumberColumn("Views (Edit)", format="%d")
            },
            use_container_width=True,
            hide_index=True
        )

        if st.button("💾 Save Changes (Update Views)"):
            edited_df['Date'] = edited_df['Date'].astype(str)
            update_data("logs", edited_df)
            st.success("Data updated in Google Sheets!")
    else:
        st.write("No records found.")

# ==========================================
# [TAB 4] Settings (Admin)
# ==========================================
with tab4:
    st.info("Manage Staff and Channel Lists here.")
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        st.markdown("#### 👤 Staff List")
        st.write(", ".join(employees_list))
        new_emp = st.text_input("Add New Staff", key="add_emp")
        if st.button("Add Staff"):
            employees_list.append(new_emp)
            # Sync lengths
            max_len = max(len(employees_list), len(channels_list))
            new_emp_series = pd.Series(employees_list + [None]*(max_len-len(employees_list)))
            new_ch_series = pd.Series(channels_list + [None]*(max_len-len(channels_list)))
            new_config = pd.DataFrame({"employees": new_emp_series, "channels": new_ch_series})
            update_data("config", new_config)
            st.rerun()

    with col_s2:
        st.markdown("#### 📺 Channel List")
        st.write(", ".join(channels_list))
        new_ch = st.text_input("Add New Channel", key="add_ch")
        if st.button("Add Channel"):
            channels_list.append(new_ch)
            # Sync lengths
            max_len = max(len(employees_list), len(channels_list))
            new_emp_series = pd.Series(employees_list + [None]*(max_len-len(employees_list)))
            new_ch_series = pd.Series(channels_list + [None]*(max_len-len(channels_list)))
            new_config = pd.DataFrame({"employees": new_emp_series, "channels": new_ch_series})
            update_data("config", new_config)
            st.rerun()
