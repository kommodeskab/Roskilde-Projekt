# dashboard.py  –  Streamlit app for RF crowd monitoring
# ---------------------------------------------------------------------------
# • NEW: Lets the user choose an arbitrary start & end date *and* time
#   window, instead of a single-day drop-down.
# • RSSI→distance helper from utils.py
# • Projects device locations to local (x, y) metres for triangulation
# • Converts results back to lat/lon and renders a PyDeck heat-map
# ---------------------------------------------------------------------------

from __future__ import annotations

import ast
from datetime import datetime, timedelta, time

import matplotlib.pyplot as plt
import mpld3
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

from triangulate import triangulate_positions
from utils import (
    COLUMNS,
    DEVICE_POSITIONS,          # original lat/lon pairs
    DEVICE_POSITIONS_XY,       # projected metres east/north of census1
    get_sheet,
    rssi_to_distance,
    xy_to_ll,
)

# ---------------------------------------------------------------------------
# Streamlit page setup and Matplotlib defaults
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Crowd Monitoring Dashboard", layout="wide")
st.title("Crowd Monitoring Dashboard")

plt.style.use("default")
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"
plt.rcParams["savefig.facecolor"] = "white"

# ---------------------------------------------------------------------------
# Data loading (cached for 10 min)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def read_data() -> pd.DataFrame:
    """Fetch Google-Sheet records and prepare a tidy DataFrame."""
    sheet = get_sheet()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(data, columns=COLUMNS)

    # safely parse the crowd_data column (string-ified dict)
    def parse_crowd(x):
        if pd.isna(x) or not isinstance(x, str) or x.strip() == "":
            return {}
        try:
            return ast.literal_eval(x)
        except (ValueError, SyntaxError):
            return {}

    df["crowd_data"] = df["crowd_data"].apply(parse_crowd)
    df["crowd_count"] = df["crowd_data"].apply(len)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # keep only rows that have at least one MAC
    df = df[df["crowd_data"].apply(bool)]

    return df


data = read_data()
if data.empty:
    st.info("No data available.")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

devices = sorted(data["device_name"].unique())
selected_devices = st.sidebar.multiselect("Select device(s)", devices, default=devices)

# ---- NEW: Date & time range pickers ---------------------------------------
min_date = data["timestamp"].dt.date.min()
max_date = data["timestamp"].dt.date.max()

start_date = st.sidebar.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)

start_time = st.sidebar.time_input("Start time", value=time(0, 0))
end_time   = st.sidebar.time_input("End time",   value=time(23, 59))

# Combine to aware datetimes (naive but consistent):
start_dt = datetime.combine(start_date, start_time)
end_dt   = datetime.combine(end_date,   end_time)

if start_dt > end_dt:
    st.sidebar.error("⚠️ Start must be before end.")
    st.stop()

plot_type = st.sidebar.radio("Visualization", ["Crowd Count", "Triangulated Positions"])

st.sidebar.markdown("### RSSI calibration")
N = st.sidebar.slider("Path-loss exponent (N)", 2.0, 4.0, 3.0, 0.1)
measured_power = st.sidebar.number_input("Measured power @ 1 m (dBm)", value=-16.0, step=0.5)

# ---------------------------------------------------------------------------
# Data subset for the chosen period
# ---------------------------------------------------------------------------
df = data[
    (data["device_name"].isin(selected_devices))
    & (data["timestamp"] >= start_dt)
    & (data["timestamp"] <= end_dt)
]

if df.empty:
    st.warning("No data in the selected interval.")
    st.stop()

# ---------------------------------------------------------------------------
# Branch 1 – crowd-count time-series
# ---------------------------------------------------------------------------
if plot_type == "Crowd Count":
    mode = st.sidebar.radio("Show as", ["Individual", "Total"])

    print(df["timestamp"].dtype)          # should say datetime64[ns, XXX]
    print(df["timestamp"].dt.tz)          # see the actual zone


    def moving_avg(series: pd.Series, w: int = 5) -> pd.Series:
        return series.rolling(window=w, min_periods=1).mean()

    fig, ax = plt.subplots()
    if mode == "Individual":
        for dev in selected_devices:
            dev_df = df[df["device_name"] == dev]
            if dev_df.empty:
                continue
            xs = dev_df["timestamp"]
            ys = moving_avg(dev_df["crowd_count"], 10).round()
            # break gaps longer than 10 min
            mask = dev_df["timestamp"].diff() < timedelta(minutes=10)
            ax.fill_between(xs, ys, alpha=0.6, label=dev, where=mask)
    else:
        summed = df.groupby("timestamp")["crowd_count"].sum().reset_index()
        xs = summed["timestamp"]
        ys = moving_avg(summed["crowd_count"], 10).round()
        mask = summed["timestamp"].diff() < timedelta(minutes=10)
        ax.fill_between(xs, ys, alpha=0.6, label="Total", where=mask)

    ax.set_xlabel("Time")
    ax.set_ylabel("Crowd count (moving-avg)")
    ax.set_title(f"Crowd Count\n{start_dt:%Y-%m-%d %H:%M} → {end_dt:%Y-%m-%d %H:%M}")
    ax.legend(loc="upper right")
    plt.tight_layout()
    fig.subplots_adjust(bottom=0.2, left=0.1)

    # Make the Matplotlib figure interactive in Streamlit
    components.html(mpld3.fig_to_html(fig), height=600)

# ---------------------------------------------------------------------------
# Branch 2 – triangulated positions with heat-map
# ---------------------------------------------------------------------------
else:  # plot_type == "Triangulated Positions"
    positions: list[dict] = []

    # Map timestamp → {device: crowd_data_dict}
    grouped = df.groupby("timestamp").apply(
        lambda g: dict(zip(g["device_name"], g["crowd_data"]))
    )

    for ts, dev_data in grouped.items():
        available_devs = set(dev_data) & DEVICE_POSITIONS_XY.keys()
        if not available_devs:
            continue

        # collect every MAC seen by any of the available devices
        all_macs = {mac for dev in available_devs for mac in dev_data[dev]}
        for mac in all_macs:
            coords: list[tuple[float, float]] = []
            dists: list[float] = []

            for dev in available_devs:
                rssi_dict = dev_data[dev]
                if mac not in rssi_dict:
                    continue

                val = rssi_dict[mac]
                avg_rssi = (
                    sum(val) / len(val) if isinstance(val, (list, tuple)) else val
                )
                dist = rssi_to_distance(avg_rssi, N=N, measured_power=measured_power)

                coords.append(DEVICE_POSITIONS_XY[dev])  # metres
                dists.append(dist)

            if len(dists) >= 3:
                coords3 = coords[:3]
                dists3 = dists[:3]
                D = np.array([dists3])

                pos_xy = triangulate_positions(D, *coords3)[0]  # (x, y) in metres
                lat, lon = xy_to_ll(*pos_xy)
                positions.append({"timestamp": ts, "lat": lat, "lon": lon})

    # --------------------------------------  visualise
    if not positions:
        st.warning(
            "No triangulated positions found - need three overlapping devices at the "
            "same timestamp and matching `device_name` entries in `DEVICE_POSITIONS`."
        )
    else:
        pos_df = pd.DataFrame(positions)

        heat_layer = pdk.Layer(
            "HeatmapLayer",
            pos_df,
            get_position="[lon, lat]",
            radiusPixels=60,
            opacity=0.9,
        )

        origin_lat, origin_lon = DEVICE_POSITIONS["census1"]

        view = pdk.ViewState(
            latitude=origin_lat,
            longitude=origin_lon,
            zoom=16,
            pitch=0,
        )

        st.subheader(
            f"Crowd density heat-map\n{start_dt:%Y-%m-%d %H:%M} → {end_dt:%Y-%m-%d %H:%M}"
        )
        st.pydeck_chart(pdk.Deck(layers=[heat_layer], initial_view_state=view))
