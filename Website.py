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
filtered_data = data[data['timestamp'].dt.date == selected_day]
filtered_data : pd.DataFrame

# make a slider for selecting the current time
current_time = st.slider(
    "Select a time",
    min_value=filtered_data['timestamp'].min().time(),
    max_value=filtered_data['timestamp'].max().time(),
    value=filtered_data['timestamp'].min().time(),
    format="HH:mm",
    step=timedelta(minutes=1),
)

# Filter the data based on the selected time
filtered_data = filtered_data[filtered_data['timestamp'].dt.time == current_time]
crowd_data = filtered_data['crowd_data'].apply(eval)

# convert the crowd_data to a numpy array
# the crowd_data is a dictionary with device names as keys and distances as values
crowd_data = pd.DataFrame(crowd_data.tolist()).to_numpy().T
estimated_positions = triangulate_positions(
    crowd_data,
    DEVICE_POSITIONS['device1'],
    DEVICE_POSITIONS['device2'],
    DEVICE_POSITIONS['device3'],
)

fig, ax = plt.subplots()
plt.scatter(estimated_positions[:, 0], estimated_positions[:, 1], c='blue', s=10, alpha=0.5)
for device, position in DEVICE_POSITIONS.items():
    ax.scatter(*position, label=device, s=100, edgecolor='black')
plt.xlim(-3, 3)
plt.ylim(-3, 3)
html_fig = mpld3.fig_to_html(fig)
components.html(html_fig, height=500, width=700)
print(estimated_positions.shape)

st.dataframe(filtered_data, use_container_width=True)