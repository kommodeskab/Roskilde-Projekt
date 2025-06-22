import streamlit as st
from utils import get_sheet, COLUMNS, DEVICE_POSITIONS
import matplotlib.pyplot as plt
import mpld3
import streamlit.components.v1 as components
import pandas as pd
from datetime import timedelta
from triangulate import triangulate_positions

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
    df['crowd_data'] = df['crowd_data'].apply(eval) 
    df['crowd_count'] = df['crowd_data'].apply(len)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df

data = read_data()

if data.empty:
    st.write("No data available.")
    st.rerun()
    
timestamps = data['timestamp'].unique()
unique_days = data['timestamp'].dt.date.unique()
selected_day = st.selectbox("Select a day", options=unique_days, key="day_selector")
filtered_data = data.loc[data['timestamp'].dt.date == selected_day]

plot_option = st.radio(
    "Select plot type",
    options=["Crowd Count", "Triangulated Positions"],
    key="plot_type"
)

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

if plot_option == "Crowd Count":
    devices = filtered_data['device_name'].unique()
    # for each device, plot the crowd count over time
    
    for device, color in zip(devices, colors):
        device_data = filtered_data.loc[filtered_data['device_name'] == device]
        device_data['timediff'] = device_data['timestamp'].diff()
        breaks = device_data['timediff'] > timedelta(minutes=10)
        device_data['group'] = breaks.cumsum()
        
        for i, (group, group_data) in enumerate(device_data.groupby('group')):
            label = device if i == 0 else None
            plt.plot(group_data['timestamp'], group_data['crowd_count'], label=label, linestyle='-', color=color)
        
    plt.xlabel("Time")
    plt.ylabel("Crowd Count")
    plt.title(f"Crowd Count on {selected_day}")
    plt.xticks(rotation=45)
    plt.legend(loc='upper left')
    plt.tight_layout()
    
    # make interactive with mpld3
    mpld3_fig = mpld3.fig_to_html(plt.gcf())
    components.html(mpld3_fig, height=600)
    
else:
    raise NotImplementedError()