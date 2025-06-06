import streamlit as st
from utils import get_sheet, COLUMNS
import matplotlib.pyplot as plt
import mpld3
import streamlit.components.v1 as components
import pandas as pd

# 'streamlit run website.py' to run the dashboard
st.title("Crowd Monitoring Dashboard")
st.write("This dashboard displays crowd monitoring data from the Google Sheet.")

@st.cache_data(ttl=600, show_spinner=False)
def read_data() -> pd.DataFrame:
    sheet = get_sheet()
    data = sheet.get_all_records()
    if not data:
        # returns an empty DataFrame
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(data, columns=COLUMNS)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df

data = read_data()

if data.empty:
    st.write("No data available.")
    st.rerun()
    
locations = data['location'].unique()
st.sidebar.title("Filter Options")
selected_location = st.sidebar.selectbox("Select Location", list(locations), key="location_filter")

st.sidebar.title("Other options")

if st.sidebar.checkbox("Show Raw Data", value=False, key="raw_data_checkbox"):
    st.dataframe(data)
    
if st.sidebar.checkbox("Show Data Summary", value=False, key="data_summary_checkbox"):
    st.write(data.describe())
    
if st.sidebar.button("Refresh Data", key="refresh_data_button"):
    st.cache_data.clear()
    st.rerun()

data = data[data['location'] == selected_location]

diff = data['timestamp'].diff().fillna(pd.Timedelta(seconds=0))
where = diff < pd.Timedelta(minutes=10)

fig = plt.figure()
plt.fill_between(data['timestamp'], data['crowd_count'], color='skyblue', where=where)
plt.xlabel('Timestamp')
plt.ylabel('Crowd Count')
plt.grid(alpha=0.1)
fig_html = mpld3.fig_to_html(fig)
components.html(fig_html, height=500)