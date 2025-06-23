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

def rssi_to_distance(rssi : float, N : float, measured_power : float) -> float:
    # rssi = Received Signal Strength Indicator
    # N = device constat, usually between 2 and 4, 2 for free space, 3 for urban areas, 4 for indoor
    # measured_power = RSSI at 1 meter distance, needs to be calibrated for each device, around -16
    return 10 ** ((measured_power - rssi) / (10 * N))

data = read_data()

if data.empty:
    st.write("No data available.")
    st.rerun()

devices = data['device_name'].unique()
unique_days = data['timestamp'].dt.date.unique()
selected_day = st.selectbox("Select a day", options=unique_days, key="day_selector")
filtered_data = data.loc[data['timestamp'].dt.date == selected_day]

plot_option = st.radio(
    "Select plot type",
    options=["Crowd Count", "Triangulated Positions"],
    key="plot_type"
)

colors = {
    'census1': '#1f77b4',
    'census2': '#ff7f0e',
    'census3': '#2ca02c',
}

if plot_option == "Crowd Count":    
    def moving_average(series : pd.Series, window_size : int=5) -> pd.Series:
        return series.rolling(window=window_size, min_periods=1).mean()
    
    for device in devices:
        device_data = filtered_data.loc[filtered_data['device_name'] == device]
        timediff = device_data['timestamp'].diff()
        xs = device_data['timestamp']
        ys = moving_average(device_data['crowd_count'], 10).round()
        where = timediff < timedelta(minutes=10)
        plt.fill_between(xs, ys, color=colors[device], alpha=0.8, label=device, where=where)
        
    plt.ylabel("Crowd Count")
    plt.title(f"Crowd Count on {selected_day}")
    plt.legend(loc='upper left')
    plt.tight_layout()
    
    # make interactive with mpld3
    mpld3_fig = mpld3.fig_to_html(plt.gcf())
    components.html(mpld3_fig, height=600)
    
else:
    raise NotImplementedError()