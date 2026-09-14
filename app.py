import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

try:
    from streamlit_autorefresh import st_autorefresh
except ModuleNotFoundError:
    def st_autorefresh(*args, **kwargs):
        return None

st.set_page_config(
    page_title="Valkyrie BMS Telemetry",
    page_icon="⚡",
    layout="wide"
)

st_autorefresh(interval=1000, key="telemetry_counter")

if "last_id" not in st.session_state:
    st.session_state.last_id = 0
if "telemetry_data" not in st.session_state:
    st.session_state.telemetry_data = pd.DataFrame()

API_URL = "http://127.0.0.1:8000/api/telemetry/latest"


def fetch_telemetry():
    try:
        response = requests.get(f"{API_URL}?limit=150&last_id={st.session_state.last_id}", timeout=0.8)
        if response.status_code == 200:
            payload = response.json()
            new_data = payload.get("data", [])
            if new_data:
                new_df = pd.DataFrame(new_data)
                if "id" in new_df.columns and not new_df.empty:
                    st.session_state.last_id = int(new_df["id"].max())

                if not st.session_state.telemetry_data.empty:
                    df = pd.concat([st.session_state.telemetry_data, new_df])
                else:
                    df = new_df
                
                df = df.tail(500).reset_index(drop=True)
                st.session_state.telemetry_data = df
    except requests.exceptions.RequestException:
        pass
    return st.session_state.telemetry_data.copy()


df = fetch_telemetry()

# Honest framing: this is a Software-in-the-Loop prototype today.
# Say the HIL part out loud in the interview — don't let the UI claim it first.
st.markdown("## ⚡ Valkyrie BMS: SIL prototype that scales to HIL")
st.caption("Same packet schema scales to real STM32 hardware via UART")

if df.empty:
    st.warning("Awaiting virtual MCU telemetry stream from `http://127.0.0.1:8000`...")
    st.stop()

df["timestamp"] = pd.to_datetime(df["timestamp"])

latest = df.iloc[-1]

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Cycle ID", int(latest["cycle_id"]))
col2.metric("Mode", str(latest["mode"]).upper())
col3.metric("Terminal Voltage", f"{latest['voltage']:.3f} V")
col4.metric("Current Draw", f"{latest['current']:.3f} A")
col5.metric("Temperature", f"{latest['temperature']:.2f} °C")

st.divider()

left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("State Gauge")
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=latest["voltage"],
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Cell Voltage (V)"},
        gauge={
            "axis": {"range": [2.5, 4.5]},
            "bar": {"color": "#00cc96"},
            "steps": [
                {"range": [2.5, 3.0], "color": "#EF553B"},
                {"range": [3.0, 4.0], "color": "#636EFA"},
                {"range": [4.0, 4.5], "color": "#FFA15A"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 4.2,
            },
        },
    ))
    fig_gauge.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

with right_col:
    st.subheader("Live dynamic waveforms")
    fig_time = go.Figure()
    fig_time.add_trace(go.Scatter(
        x=df["timestamp"], y=df["voltage"], mode="lines",
        name="Voltage (V)", line=dict(color="#00cc96", width=2),
    ))
    fig_time.add_trace(go.Scatter(
        x=df["timestamp"], y=df["current"], mode="lines",
        name="Current (A)", yaxis="y2",
        line=dict(color="#FFA15A", width=1.5, dash="dot"),
    ))
    fig_time.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(title="Timestamp"),
        yaxis=dict(title="Voltage (V)", side="left"),
        yaxis2=dict(title="Current (A)", side="right", overlaying="y"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_time, use_container_width=True)

st.subheader("Thermal profile")
fig_temp = go.Figure()
fig_temp.add_trace(go.Scatter(
    x=df["timestamp"], y=df["temperature"], mode="lines+markers",
    name="Temp (°C)", line=dict(color="#EF553B", width=2),
))
fig_temp.update_layout(
    height=220,
    margin=dict(l=20, r=20, t=10, b=10),
    xaxis=dict(title="Timestamp"),
    yaxis=dict(title="Temperature (°C)"),
)
st.plotly_chart(fig_temp, use_container_width=True)