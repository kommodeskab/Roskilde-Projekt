# dashboard.py – Streamlit app for RF crowd monitoring
# ---------------------------------------------------------------------------
# • NEW: Lets the user choose an arbitrary start & end date *and* time
#   window, instead of a single-day drop-down.
# • RSSI→distance helper from utils.py
# • Projects device locations to local (x, y) metres for triangulation
# • Converts results back to lat/lon and renders a PyDeck heat-map
# • NEW (2025‑07‑01): “Unique (across devices)” crowd‑count mode
# • MODIFIED (2025-07-03): Replaced PyDeck with interactive Folium map,
#   allowing user-placed markers for dynamic triangulation.
# ---------------------------------------------------------------------------

from __future__ import annotations

import ast
from datetime import datetime, timedelta, time

import folium
import matplotlib.pyplot as plt
import mpld3
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from folium.plugins import HeatMap, MousePosition
from folium.raster_layers import ImageOverlay
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium

from triangulate import triangulate_positions
from utils import (
    COLUMNS,
    # DEVICE_POSITIONS,        # No longer primary source for triangulation
    # DEVICE_POSITIONS_XY,     # Will be generated on-the-fly from markers
    get_sheet,
    ll_to_xy,                # ASSUMPTION: You have this function in utils.py
    rssi_to_distance,
    xy_to_ll,
)


# ---------------------------------------------------------------------------
# Streamlit page setup and Matplotlib defaults
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Crowd Monitoring Dashboard", layout="wide")
st.title("Crowd Monitoring Dashboard")
st_autorefresh(interval=60_000, key="dashboard_refresher")
plt.style.use("default")
# ... (Matplotlib rcParams setup remains the same) ...

# ---------------------------------------------------------------------------
# Data loading (cached for 10 min)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="Fetching latest data...")
def read_data() -> pd.DataFrame:
    """Fetch Google‑Sheet records and prepare a tidy DataFrame."""
    sheet = get_sheet()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(data, columns=COLUMNS)

    def parse_crowd(x):
        if pd.isna(x) or not isinstance(x, str) or x.strip() == "": return {}
        try: return ast.literal_eval(x)
        except (ValueError, SyntaxError): return {}

    df["crowd_data"] = df["crowd_data"].apply(parse_crowd)
    df["crowd_count"] = df["crowd_data"].apply(len)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    df = df[df["crowd_data"].apply(bool)]

    return df


data = read_data()
if data.empty:
    st.info("No data available.")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.title("Controls")
devices = sorted(data["device_name"].unique())
selected_devices = st.sidebar.multiselect("Select device(s) to process", devices, default=devices)

min_date, max_date = data["timestamp"].dt.date.min(), data["timestamp"].dt.date.max()
start_date = st.sidebar.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)
start_time = st.sidebar.time_input("Start time", value=time(0, 0))
end_time   = st.sidebar.time_input("End time",   value=time(23, 59))

start_dt, end_dt = datetime.combine(start_date, start_time), datetime.combine(end_date, end_time)
if start_dt > end_dt:
    st.sidebar.error("⚠️ Start must be before end.")
    st.stop()

plot_type = st.sidebar.radio("Visualization", ["Crowd Count", "Triangulated Positions"])

st.sidebar.markdown("### RSSI calibration")
N = st.sidebar.slider("Path‑loss exponent (N)", 2.0, 4.0, 3.0, 0.1)
measured_power = st.sidebar.number_input("Measured power @ 1m (dBm)", value=-16.0, step=0.5)

# ---------------------------------------------------------------------------
# Data subset for the chosen period
# ---------------------------------------------------------------------------
df = data[
    (data["device_name"].isin(selected_devices))
    & (data["timestamp"] >= start_dt)
    & (data["timestamp"] <= end_dt)
]

if df.empty:
    st.warning("No data in the selected interval for the chosen devices.")
    st.stop()

# ---------------------------------------------------------------------------
# Branch 1 – crowd‑count time‑series
# ---------------------------------------------------------------------------
if plot_type == "Crowd Count":
    st.header(f"Crowd Count Analysis")
    mode = st.radio(
        "Crowd count mode",
        ["Individual", "Total", "Unique (across devices)"],
        index=0,
        horizontal=True,
    )
    # ... (The entire crowd-count plotting logic remains exactly the same) ...
    def moving_avg(series: pd.Series, w: int = 5) -> pd.Series:
        return series.rolling(window=w, min_periods=1).mean()

    fig, ax = plt.subplots()

    if mode == "Individual":
        for dev in selected_devices:
            dev_df = df[df["device_name"] == dev]
            if dev_df.empty: continue
            xs = dev_df["timestamp"]
            ys = moving_avg(dev_df["crowd_count"], 10).round()
            mask = dev_df["timestamp"].diff() < timedelta(minutes=10)
            ax.fill_between(xs, ys, alpha=0.6, label=dev, where=mask)
    elif mode == "Total":
        summed = df.groupby("timestamp")["crowd_count"].sum().reset_index()
        xs = summed["timestamp"]
        ys = moving_avg(summed["crowd_count"], 10).round()
        mask = summed["timestamp"].diff() < timedelta(minutes=10)
        ax.fill_between(xs, ys, alpha=0.6, label="Total", where=mask)
    else:  # mode == "Unique (across devices)"
        unique_counts = (
            df.groupby("timestamp")["crowd_data"]
            .apply(lambda s: len({mac for d in s for mac in d.keys()}))
            .reset_index(name="unique_count")
        )
        xs = unique_counts["timestamp"]
        ys = moving_avg(unique_counts["unique_count"], 10).round()
        mask = unique_counts["timestamp"].diff() < timedelta(minutes=10)
        ax.fill_between(xs, ys, alpha=0.6, label="Unique", where=mask)

    ax.set_xlabel("Time")
    ax.set_ylabel("Crowd count (moving‑avg)")
    ax.set_title(f"Crowd Count\n{start_dt:%Y‑%m‑%d %H:%M} → {end_dt:%Y‑%m‑%d %H:%M}")
    ax.legend(loc="upper right")
    plt.tight_layout()
    fig.subplots_adjust(bottom=0.2, left=0.1)
    components.html(mpld3.fig_to_html(fig), height=600)

# ---------------------------------------------------------------------------
# Branch 2 – Interactive Triangulation & Heatmap
# ---------------------------------------------------------------------------
# (Your script's first half remains the same)
# ...

# ---------------------------------------------------------------------------
# Branch 2 – Interactive Triangulation & Heatmap
# ---------------------------------------------------------------------------
else: # plot_type == "Triangulated Positions"
    st.header("Interactive Triangulation Map")
    st.markdown(
        """
        **Step 1:** Click on the map to place up to 3 markers for your sensor locations.
        **Step 2:** Use the sidebar to assign a device to each marker.
        **Step 3:** Click 'Triangulate' to generate the initial crowd heatmap. The map will then auto-update if you adjust the RSSI parameters.
        """
    )
    
    # --- Folium Map & Image Overlay Setup ---
    UL, LL, LR, UR = (55.631644, 12.053289), (55.606569, 12.049529), (55.605214, 12.112965), (55.630122, 12.115078)
    bounds = [[min(LL[0], LR[0]), min(LL[1], UL[1])], [max(UL[0], UR[0]), max(UR[1], LR[1])]]
    centre_lat, centre_lon = (UL[0] + LR[0]) / 2, (UL[1] + UR[1]) / 2

    # --- Session State Management ---
    if "markers" not in st.session_state:
        st.session_state["markers"] = [] # List of {'lat': float, 'lon': float, 'device': str}
    if "heatmap_data" not in st.session_state:
        st.session_state["heatmap_data"] = []
    if "last_click" not in st.session_state:
        st.session_state["last_click"] = None
    # NEW: State flag to control when calculations should run
    if "run_triangulation" not in st.session_state:
        st.session_state["run_triangulation"] = False

    # --- Sidebar Marker Controls ---
    with st.sidebar:
        st.markdown("### Marker Controls")
        if st.button("Clear All Markers", use_container_width=True):
            st.session_state["markers"] = []
            st.session_state["heatmap_data"] = []
            st.session_state["last_click"] = None
            # CHANGED: Reset the triangulation flag
            st.session_state["run_triangulation"] = False
            st.rerun()

        # ... (Marker assignment logic remains the same) ...
        st.markdown("#### Placed Markers")
        assigned_devices = []
        for i, mk in enumerate(st.session_state["markers"]):
            st.markdown(f"**Marker {i+1}**")
            unassigned_devices = [d for d in selected_devices if d not in assigned_devices or d == mk.get("device")]
            current_device = mk.get("device", "Not Assigned")
            options = ["Not Assigned"] + sorted(unassigned_devices)
            try:
                current_index = options.index(current_device)
            except ValueError:
                current_index = 0
            
            new_device = st.selectbox(f"Assign Device to Marker {i+1}", options, index=current_index, key=f"device_select_{i}")
            st.session_state["markers"][i]['device'] = new_device if new_device != "Not Assigned" else None
            
            if st.session_state["markers"][i]['device']:
                assigned_devices.append(st.session_state["markers"][i]['device'])
            st.text(f"Lat: {mk['lat']:.5f}, Lon: {mk['lon']:.5f}")

    # --- Triangulation Trigger ---
    can_triangulate = (
        len(st.session_state["markers"]) == 3 and
        all(mk.get("device") for mk in st.session_state["markers"]) and
        len(set(mk['device'] for mk in st.session_state["markers"])) == 3
    )
    
    # CHANGED: The button now just sets the flag to True
    if st.sidebar.button("Triangulate & Generate Heatmap", disabled=not can_triangulate, use_container_width=True):
        st.session_state['run_triangulation'] = True
        st.rerun() # Force a rerun to start the calculation immediately

    # --- Calculation Logic ---
    # CHANGED: This logic now runs if the flag is True, not just on button click
    if can_triangulate and st.session_state.get('run_triangulation'):
        positions = []
        with st.spinner("Calculating heatmap..."):
            # 1. Create lookups from markers
            marker_devices = {mk['device']: (mk['lat'], mk['lon']) for mk in st.session_state["markers"]}
            origin_device = st.session_state["markers"][0]['device']
            origin_ll = marker_devices[origin_device]
            
            DEVICE_POSITIONS_XY_DYNAMIC = {dev: ll_to_xy(ll[0], ll[1], origin_ll[0], origin_ll[1]) for dev, ll in marker_devices.items()}

            # 2. Group data by timestamp
            grouped = df.groupby("timestamp").apply(lambda g: dict(zip(g["device_name"], g["crowd_data"])))

            # 3. Perform triangulation
            for ts, dev_data in grouped.items():
                available_devs = set(dev_data) & set(marker_devices.keys())
                if len(available_devs) < 3: continue

                all_macs = {mac for dev in available_devs for mac in dev_data[dev]}
                for mac in all_macs:
                    coords, dists, rssi_devs = [], [], []
                    for dev in available_devs:
                        if mac in dev_data[dev]:
                            val = dev_data[dev][mac]
                            avg_rssi = sum(val) / len(val) if isinstance(val, list) else val
                            # USE THE LIVE SLIDER VALUES
                            dist = rssi_to_distance(avg_rssi, N=N, measured_power=measured_power)
                            coords.append(DEVICE_POSITIONS_XY_DYNAMIC[dev])
                            dists.append(dist)
                            rssi_devs.append(dev)

                    if len(dists) >= 3:
                        coords3, dists3 = [], []
                        required_devices = list(marker_devices.keys())
                        for d_name in required_devices:
                            try:
                                idx = rssi_devs.index(d_name)
                                coords3.append(coords[idx])
                                dists3.append(dists[idx])
                            except ValueError:
                                break # One of the required devices didn't see this MAC
                        
                        if len(dists3) == 3:
                            pos_xy = triangulate_positions(np.array([dists3]), *coords3)[0]
                            lat, lon = xy_to_ll(pos_xy[0], pos_xy[1], origin_ll[0], origin_ll[1])
                            positions.append([lat, lon])
        
        # Store the results for the map to use
        st.session_state["heatmap_data"] = positions
        if not positions:
            st.warning("Could not triangulate any positions with the current settings. Ensure the selected devices have overlapping data.")
        else:
            # This success message will appear on every update
            st.toast(f"Heatmap updated with {len(positions)} data points.")

    # --- Folium Map Rendering (remains the same) ---
    m = folium.Map(location=[centre_lat, centre_lon], zoom_start=15, control_scale=True)
    ImageOverlay(name="Festival Map", image="festival_map.jpg", bounds=bounds, opacity=0.9, zindex=1).add_to(m)

    for mk in st.session_state["markers"]:
        folium.Marker(location=[mk['lat'], mk['lon']], tooltip=f"Device: {mk.get('device', 'Unassigned')}", icon=folium.Icon(color='red', icon='wifi')).add_to(m)
        
    if st.session_state["heatmap_data"]:
        HeatMap(st.session_state["heatmap_data"], radius=20, blur=20).add_to(m)

    # ... (Map display and click-handling logic remains the same) ...
    map_data = st_folium(m, key="folium_map", height=600, width="100%")
    if map_data and (click := map_data.get("last_clicked")):
        if click != st.session_state.get("last_click"):
            st.session_state["last_click"] = click
            if len(st.session_state["markers"]) < 3:
                st.session_state["markers"].append({'lat': click['lat'], 'lon': click['lng'], 'device': None})
                # If markers are changed, force a re-triangulation if it was already running
                if st.session_state.get('run_triangulation'):
                    st.rerun()
                else:
                    st.rerun()
    
    if len(st.session_state["markers"]) >= 3:
        st.info("ℹ️ Maximum of 3 markers placed. Clear markers to start over.")