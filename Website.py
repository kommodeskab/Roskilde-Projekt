import streamlit as st
from utils import read_data
import matplotlib.pyplot as plt
import mpld3
import streamlit.components.v1 as components

# 'streamlit run website.py' to run the dashboard
st.title("Crowd Monitoring Dashboard")
st.write("This dashboard displays crowd monitoring data from the Google Sheet.")

data = read_data()

fig = plt.figure()
plt.fill_between(data['timestamp'], data['crowd_count'], color='skyblue', alpha=0.9)
plt.xlabel('Timestamp')
plt.ylabel('Crowd Count')
fig_html = mpld3.fig_to_html(fig)
components.html(fig_html, height=500)