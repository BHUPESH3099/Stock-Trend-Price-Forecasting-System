import streamlit as st
import requests
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# Backend URL
BACKEND_URL = "https://your-backend-service.onrender.com/stock"


# --- Page Setup ---
st.set_page_config(
    page_title="Trading Terminal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Hide Streamlit default UI ---
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}   /* Hides the 3-dot menu */
    footer {visibility: hidden;}      /* Hides Streamlit footer */
    header {visibility: hidden;}      /* Hides Deploy button & top bar */
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- Dark Theme CSS ---
st.markdown(
    """
    <style>
    body {background-color: #0e1117; color: white;}
    .stApp {background-color: #0e1117;}

    /* Fixed Top Bar */
    .top-bar {
        position: fixed; top: 0; left: 0; right: 0; z-index: 999;
        background-color: #161a23; padding: 12px 20px;
        border-bottom: 1px solid #333; display: flex; align-items: center;
    }
    .top-bar input, .top-bar button, .top-bar .stSlider {margin-right: 15px;}
    .block-container {padding-top: 110px;}  /* Push content below fixed bar */

    /* Metric Cards */
    .metric-card {
        background:#1c1f2b; padding:15px; border-radius:10px; text-align:center;
        color:white; font-weight:bold; font-size:16px;
    }
    .section-title {
        font-size:18px; font-weight:bold; margin-top:20px; color:#00ff85;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Top Bar ---
st.markdown(
    """
    <div class="top-bar">
        <h2 style="color:white; margin-right:30px;">📊 Trading Terminal</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# Inputs at top (Search, Days, Button)
col_search, col_days, col_btn = st.columns([3, 2, 1])
with col_search:
    ticker = st.text_input("Search Symbol...", value="INFY", label_visibility="collapsed")
with col_days:
    days = st.slider("Days", 30, 365, 120, label_visibility="collapsed")
with col_btn:
    fetch_data = st.button("Fetch Data")

# --- Data Fetch ---
if fetch_data:
    if not ticker.strip():
        st.warning("Please enter a ticker.")
    else:
        params = {"symbol": ticker.strip(), "days": int(days)}
        try:
            resp = requests.get(BACKEND_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            st.stop()

        chart = data.get("chart", [])

        if chart and isinstance(chart, list):
            latest = chart[-1]  # dictionary with capitalized keys

            live = {
                "date": latest.get("Date"),
                "open": latest.get("Open"),
                "dayHigh": latest.get("High"),
                "dayLow": latest.get("Low"),
                "lastPrice": latest.get("Close"),
                "volume": latest.get("Volume")
            }

            open_val = f"{live['open']:.2f}" if live['open'] is not None else "-"
            high_val = f"{live['dayHigh']:.2f}" if live['dayHigh'] is not None else "-"
            low_val = f"{live['dayLow']:.2f}" if live['dayLow'] is not None else "-"
            close_val = f"{live['lastPrice']:.2f}" if live['lastPrice'] is not None else "-"
            vol_val = f"{live['volume']:,}" if live['volume'] is not None else "-"

            st.markdown(f"### 🔔 Live Quote ({live['date'][:10]})")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.markdown(f"<div class='metric-card'><b>CLOSE</b><br>{close_val}</div>", unsafe_allow_html=True)
            col2.markdown(f"<div class='metric-card'><b>OPEN</b><br>{open_val}</div>", unsafe_allow_html=True)
            col3.markdown(f"<div class='metric-card'><b>HIGH</b><br>{high_val}</div>", unsafe_allow_html=True)
            col4.markdown(f"<div class='metric-card'><b>LOW</b><br>{low_val}</div>", unsafe_allow_html=True)
            col5.markdown(f"<div class='metric-card'><b>VOLUME</b><br>{vol_val}</div>", unsafe_allow_html=True)

        else:
            st.info("No live data available.")


        st.markdown("---")

        # --- Layout: Chart (left) and Indicators (right) ---
        left, right = st.columns([3, 1])

        # --- Candlestick + Volume ---
        with left:
            chart = data.get("chart")
            if chart:
                df = pd.DataFrame(chart)
                df["Date"] = pd.to_datetime(df["Date"])
                df = df.sort_values("Date")

                # --- Create Subplots: 2 rows, shared x-axis ---
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    row_heights=[0.7, 0.3],
                    vertical_spacing=0.05
                )

                # --- Candlestick (Top) ---
                fig.add_trace(
                    go.Candlestick(
                        x=df["Date"],
                        open=df["Open"], high=df["High"],
                        low=df["Low"], close=df["Close"],
                        name="Candlestick",
                        increasing_line_color="green",
                        decreasing_line_color="red"
                    ),
                    row=1, col=1
                )

                # --- Volume (Bottom) with Green/Red coloring ---
                colors = ["green" if c >= o else "red" for c, o in zip(df["Close"], df["Open"])]
                fig.add_trace(
                    go.Bar(
                        x=df["Date"], y=df["Volume"],
                        marker_color=colors,
                        opacity=0.7,
                        name="Volume"
                    ),
                    row=2, col=1
                )

                # --- Layout with Borders ---
                fig.update_layout(
                    height=700,
                    xaxis_rangeslider_visible=False,
                    paper_bgcolor="#0e1117",
                    plot_bgcolor="#0e1117",
                    font=dict(color="white"),
                    margin=dict(t=30, b=10, l=10, r=10),
                    yaxis=dict(title="Price", showgrid=True, gridcolor="#333"),
                    yaxis2=dict(title="Volume", showgrid=True, gridcolor="#333"),

                    # Border effect
                    shapes=[
                        # Border around candlestick chart
                        dict(
                            type="rect",
                            xref="paper", yref="paper",
                            x0=0, y0=0.35, x1=1, y1=1,
                            line=dict(color="white", width=1)
                        ),
                        # Border around volume chart
                        dict(
                            type="rect",
                            xref="paper", yref="paper",
                            x0=0, y0=0, x1=1, y1=0.32,
                            line=dict(color="white", width=1)
                        )
                    ]
                )

                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("No chart data available.")

        # --- Indicators / Side Panel ---
        with right:
            chart = data.get("chart", [])

            if chart and isinstance(chart, list):
                latest = chart[-1]  # dictionary with capitalized keys

                rsi_val = latest.get("RSI")
                macd_val = latest.get("MACD_12_26_9")  
                
                rsi = f"{rsi_val:.2f}" if rsi_val is not None else "-"
                macd = f"{macd_val:.2f}" if macd_val is not None else "-"
                st.markdown('<p class="section-title">📊 Indicators</p>', unsafe_allow_html=True)
                indicators = data.get("indicators", {
                    "RSI": f"{rsi}",
                    "MACD": f"{macd}",
                    "STOCH": "78.9 (Overbought)"
                })
            else:
                st.info("No live data available.")
            for k, v in indicators.items():
                st.write(f"**{k}:** {v}")

            st.markdown('<p class="section-title">🎯 Price Prediction</p>', unsafe_allow_html=True)
            st.success("Outlook: BULLISH\nTargets: $200, $215")

            st.markdown('<p class="section-title">📌 Support & Resistance</p>', unsafe_allow_html=True)
            sr_levels = data.get("levels", {
                "R3": 198.70, "R2": 195.30, "R1": 194.10,
                "S1": 188.20, "S2": 184.20, "S3": 180.90
            })
            for k, v in sr_levels.items():
                st.write(f"**{k}:** {v}")

            st.markdown('<p class="section-title">📰 News & Alerts</p>', unsafe_allow_html=True)
            news_list = data.get("news", [
                "TSLA Q4 Earnings Exceed Estimates",
                "New Gigafactory Announced",
                "Price Alert: TSLA crosses $900"
            ])
            for n in news_list:
                st.info(n)

        # --- Last 10 Days Table ---
        st.markdown('<p class="section-title">📅 Last 10 Days OHLCV</p>', unsafe_allow_html=True)
        if chart:
            latest_df = df.sort_values(by="Date", ascending=False).head(10).reset_index(drop=True)
            st.dataframe(latest_df, hide_index=True)

