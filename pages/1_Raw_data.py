from utils import read_data
import streamlit as st

data = read_data()
if data.empty:
    st.write("No data available.")
    st.rerun()
    
st.dataframe(data)
    