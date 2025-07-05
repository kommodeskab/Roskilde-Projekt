# dashboard.py – Streamlit app for RF crowd monitoring
# ---------------------------------------------------------------------------
# • NEW: Lets the user choose an arbitrary start & end date *and* time
#   window, instead of a single-day drop-down.
# • RSSI→distance helper from utils.py
# • Projects device locations to local (x, y) metres for triangulation
# • Converts results back to lat/lon and renders a Folium heat-map
# • NEW (2025-07-01): “Unique (across devices)” crowd-count mode
# • MODIFIED (2025-07-03): Replaced PyDeck with interactive Folium map,
#   allowing user-placed markers for dynamic triangulation.
# • MODIFIED (2025-07-03): Added heat-map time-window slider (1–60 min).
# • FIXED (2025-07-03): moving_avg now uses a DatetimeIndex so
#   Pandas understands string offsets like "30min".
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
from folium.plugins import HeatMap
from folium.raster_layers import ImageOverlay
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium

from triangulate import triangulate_positions
from utils import (
    COLUMNS,
    get_sheet,
    ll_to_xy,
    rssi_to_distance,
    xy_to_ll,
)

# ---------------------------------------------------------------------------
# Streamlit page setup and Matplotlib defaults
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Crowd Monitoring Dashboard", layout="wide")
st.title("Crowd Monitoring Dashboard")
plt.style.use("default")
# (custom Matplotlib rcParams go here if needed)

# ---------------------------------------------------------------------------
# Data loading (cached for 10 min)
# ---------------------------------------------------------------------------

def parse_dict_string(dict_string: str) -> dict:
    result_dict = {}
    content = dict_string.strip().strip('{}')

    if not content:
        return result_dict

    parts = content.split(', ')

    for part in parts:
        try:
            key_str, value_str = part.split(': ', 1)
        except ValueError:
            continue

        key = key_str.strip().strip("'")

        try:
            value = int(value_str.strip())
        except ValueError:
            continue

        result_dict[key] = value

    return result_dict

@st.cache_data(ttl=250, show_spinner="Fetching latest data…")
def read_data() -> pd.DataFrame:
    """Fetch Google-Sheet records and prepare a tidy DataFrame."""
    sheet = get_sheet()
    data = sheet.get_all_records()
    
    if not data:
        return pd.DataFrame(columns=COLUMNS)


    df = pd.DataFrame(data, columns=COLUMNS)

    def parse_crowd(x):
        if pd.isna(x) or not isinstance(x, str) or x.strip() == "":
            return {}
        try:
            return parse_dict_string(x)
        except (ValueError, SyntaxError):
            return {}

    print("Parsing crowd data…")
    df["crowd_data"] = df["crowd_data"].apply(parse_crowd)

    print("Converting timestamps to datetime objects…")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    
    def merge_dicts(dicts):
        merged = {}
        for d in dicts:
            merged.update(d)
        return merged

    df['time_bin'] = df['timestamp'].dt.floor('10T')

    df = (
        df.groupby(['device_name', 'time_bin'], as_index=False)
        .agg({'crowd_data': merge_dicts})
    )

    # Optional: Rename 'time_bin' back to 'timestamp' if desired
    df.rename(columns={'time_bin': 'timestamp'}, inplace=True)
    df['crowd_count'] = df['crowd_data'].apply(len)
    
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
N = st.sidebar.slider("Path-loss exponent (N)", 2.0, 4.0, 3.0, 0.1)
measured_power = st.sidebar.number_input("Measured power @ 1 m (dBm)", value=-16.0, step=0.5)

st.sidebar.markdown("### Heat-map time window")
window_minutes = st.sidebar.slider(
    "Minutes shown in heat-map",
    min_value=1,
    max_value=60,
    value=10,
    step=1,
)

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
# Helper – time-aware rolling mean
# ---------------------------------------------------------------------------
def moving_avg(series: pd.Series, window: str = "30min") -> pd.Series:
    """
    Return the rolling mean over the given *time* window.

    * `series` **must** have a DatetimeIndex.
    * `window` may be a string offset like `"30min"` or `"2h"`.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("moving_avg expects the Series index to be a DatetimeIndex")
    return series.sort_index().rolling(window=window, min_periods=1).mean()

# ---------------------------------------------------------------------------
# Branch 1 – crowd-count time-series
# ---------------------------------------------------------------------------
if plot_type == "Crowd Count":
    st.header("Crowd Count Analysis")
    mode = st.radio(
        "Crowd count mode",
        ["Individual", "Total", "Unique (across devices)"],
        index=0,
        horizontal=True,
    )

    fig, ax = plt.subplots()

    if mode == "Individual":
        for dev in selected_devices:
            dev_df = df[df["device_name"] == dev]
            if dev_df.empty:
                continue
            series = dev_df.set_index("timestamp")["crowd_count"]
            ys = moving_avg(series, "30min").round()
            xs = ys.index
            mask = dev_df["timestamp"].diff() < timedelta(minutes=15)
            ax.fill_between(xs, ys, alpha=0.6, label=dev, where=mask)

    elif mode == "Total":
        summed = (
            df.groupby("timestamp")["crowd_count"]
            .sum()
            .sort_index()
        )
        ys = moving_avg(summed, "30min").round()
        xs = ys.index
        mask = xs.to_series().diff() < timedelta(minutes=15)
        ax.fill_between(xs, ys, alpha=0.6, label="Total", where=mask)

    else:  # Unique across devices
        unique_series = (
            df.groupby("timestamp")["crowd_data"]
            .apply(lambda s: len({mac for d in s for mac in d.keys()}))
            .sort_index()
        )
        ys = moving_avg(unique_series, "30min").round()
        xs = ys.index
        mask = xs.to_series().diff() < timedelta(minutes=15)
        ax.fill_between(xs, ys, alpha=0.6, label="Unique", where=mask)

    ax.set_xlabel("Time")
    ax.set_ylabel("Crowd count (moving-avg)")
    ax.set_title(f"Crowd Count\n{start_dt:%Y-%m-%d %H:%M} → {end_dt:%Y-%m-%d %H:%M}")
    ax.legend(loc="upper right")
    plt.tight_layout()
    fig.subplots_adjust(bottom=0.2, left=0.1)
    components.html(mpld3.fig_to_html(fig), height=600)

# ---------------------------------------------------------------------------
# Branch 2 – Interactive Triangulation & Heat-map
# ---------------------------------------------------------------------------
else:  # plot_type == "Triangulated Positions"
    st.header("Interactive Triangulation Map")
    st.markdown(
        """
        **Step 1:** Click on the map to place up to 3 markers for your sensor locations.  
        **Step 2:** Assign a device to each marker in the sidebar.  
        **Step 3:** Click **Triangulate** to generate the crowd heat-map.  
        The map auto-updates when you change RSSI or the time-window slider.
        """
    )

    # --- Folium Map & Image Overlay setup ---
    UL, LL, LR, UR = (
        (55.631644, 12.053289),
        (55.606569, 12.049529),
        (55.605214, 12.112965),
        (55.630122, 12.115078),
    )
    bounds = [
        [min(LL[0], LR[0]), min(LL[1], UL[1])],
        [max(UL[0], UR[0]), max(UR[1], LR[1])],
    ]
    centre_lat, centre_lon = (UL[0] + LR[0]) / 2, (UL[1] + UR[1]) / 2

    # --- Session-state ---
    if "markers" not in st.session_state:
        st.session_state["markers"] = []          # [{'lat':…, 'lon':…, 'device':…}]
    if "heatmap_data" not in st.session_state:
        st.session_state["heatmap_data"] = []
    if "last_click" not in st.session_state:
        st.session_state["last_click"] = None
    if "run_triangulation" not in st.session_state:
        st.session_state["run_triangulation"] = False

    # --- Sidebar marker controls ---
    with st.sidebar:
        st.markdown("### Marker Controls")
        if st.button("Clear All Markers", use_container_width=True):
            st.session_state["markers"].clear()
            st.session_state["heatmap_data"].clear()
            st.session_state["last_click"] = None
            st.session_state["run_triangulation"] = False
            st.rerun()

        st.markdown("#### Placed Markers")
        assigned_devices: list[str] = []
        for i, mk in enumerate(st.session_state["markers"]):
            st.markdown(f"**Marker {i+1}**")
            unassigned_devices = [
                d for d in selected_devices
                if d not in assigned_devices or d == mk.get("device")
            ]
            options = ["Not Assigned"] + sorted(unassigned_devices)
            current_device = mk.get("device", "Not Assigned")
            current_idx = options.index(current_device) if current_device in options else 0
            new_device = st.selectbox(
                f"Assign Device to Marker {i+1}",
                options,
                index=current_idx,
                key=f"device_select_{i}",
            )
            mk["device"] = new_device if new_device != "Not Assigned" else None
            if mk["device"]:
                assigned_devices.append(mk["device"])
            st.text(f"Lat: {mk['lat']:.5f}, Lon: {mk['lon']:.5f}")

    # --- Triangulation trigger ---
    can_triangulate = (
        len(st.session_state["markers"]) == 3
        and all(mk.get("device") for mk in st.session_state["markers"])
        and len({mk["device"] for mk in st.session_state["markers"]}) == 3
    )
    if st.sidebar.button(
        "Triangulate & Generate Heat-map",
        disabled=not can_triangulate,
        use_container_width=True,
    ):
        st.session_state["run_triangulation"] = True
        st.rerun()

    # --- Calculation logic ---
    if can_triangulate and st.session_state["run_triangulation"]:
        positions: list[list[float]] = []
        with st.spinner("Calculating heat-map…"):
            # 0. Restrict df to trailing *window_minutes*
            window_end   = end_dt
            window_start = window_end - timedelta(minutes=window_minutes)
            df_window = df[
                (df["timestamp"] >= window_start) & (df["timestamp"] <= window_end)
            ]

            # 1. Build look-ups from markers
            marker_devices = {
                mk["device"]: (mk["lat"], mk["lon"]) for mk in st.session_state["markers"]
            }
            origin_device = st.session_state["markers"][0]["device"]
            origin_ll = marker_devices[origin_device]
            DEVICE_POSITIONS_XY_DYNAMIC = {
                dev: ll_to_xy(ll[0], ll[1], origin_ll[0], origin_ll[1])
                for dev, ll in marker_devices.items()
            }

            # 2. Group by timestamp
            grouped = df_window.groupby("timestamp").apply(
                lambda g: dict(zip(g["device_name"], g["crowd_data"]))
            )

            # 3. Triangulate
            for _, dev_data in grouped.items():
                available_devs = set(dev_data) & set(marker_devices.keys())
                if len(available_devs) < 3:
                    continue
                all_macs = {mac for d in available_devs for mac in dev_data[d]}
                for mac in all_macs:
                    coords, dists, rssi_devs = [], [], []
                    for dev in available_devs:
                        if mac in dev_data[dev]:
                            val = dev_data[dev][mac]
                            avg_rssi = sum(val) / len(val) if isinstance(val, list) else val
                            dist = rssi_to_distance(avg_rssi, N=N, measured_power=measured_power)
                            coords.append(DEVICE_POSITIONS_XY_DYNAMIC[dev])
                            dists.append(dist)
                            rssi_devs.append(dev)
                    if len(dists) >= 3:
                        coords3, dists3 = [], []
                        for d_name in marker_devices.keys():
                            try:
                                idx = rssi_devs.index(d_name)
                                coords3.append(coords[idx])
                                dists3.append(dists[idx])
                            except ValueError:
                                break
                        if len(dists3) == 3:
                            pos_xy = triangulate_positions(np.array([dists3]), *coords3)[0]
                            lat, lon = xy_to_ll(pos_xy[0], pos_xy[1], origin_ll[0], origin_ll[1])
                            positions.append([lat, lon])

        st.session_state["heatmap_data"] = positions
        if positions:
            st.toast(f"Heat-map updated with {len(positions)} data points.")
        else:
            st.warning(
                "Could not triangulate any positions with the current settings. "
                "Ensure the selected devices have overlapping data."
            )

    # --- Folium map rendering ---
    m = folium.Map(location=[centre_lat, centre_lon], zoom_start=15, control_scale=True)
    ImageOverlay(
        name="Festival Map",
        image="festival_map.jpg",
        bounds=bounds,
        opacity=0.9,
        zindex=1,
    ).add_to(m)

    for mk in st.session_state["markers"]:
        folium.Marker(
            location=[mk["lat"], mk["lon"]],
            tooltip=f"Device: {mk.get('device', 'Unassigned')}",
            icon=folium.Icon(color="red", icon="wifi"),
        ).add_to(m)

    if st.session_state["heatmap_data"]:
        HeatMap(st.session_state["heatmap_data"], radius=20, blur=20).add_to(m)

    map_data = st_folium(m, key="folium_map", height=600, width="100%")
    if map_data and (click := map_data.get("last_clicked")):
        if click != st.session_state.get("last_click"):
            st.session_state["last_click"] = click
            if len(st.session_state["markers"]) < 3:
                st.session_state["markers"].append(
                    {"lat": click["lat"], "lon": click["lng"], "device": None}
                )
                st.rerun()

    if len(st.session_state["markers"]) >= 3:
        st.info("ℹ️ Maximum of 3 markers placed. Clear markers to start over.")
