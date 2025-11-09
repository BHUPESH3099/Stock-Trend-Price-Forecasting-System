import streamlit as st
import requests
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# Backend URL (Assumed to be running)
BACKEND_URL = "https://stock-trend-price-forecasting-system.onrender.com/stock"

# --- Streamlit Page Setup ---
st.set_page_config(
    page_title="Pro Stock Trading Terminal",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# --- New Modern Light Theme CSS & Header Fix ---
st.markdown(
    """
    <style>
    /* Global Background: Light Gray/White */
    body, .stApp {background-color: #f0f2f6;} 
    .stApp > header {display: none;} /* Hide Streamlit's default header */
    
    /* Hide Streamlit Default UI */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar Styling */
    .stSidebar {
        background-color: #f0f2f6 !important; /* Light gray sidebar background */
        color: #1c1c1c; 
        z-index: 10000; /* Sidebar must be accessible */
    }
    
    /* Fixed Top Bar (Header/Title) */
    .top-bar-controls {
        position: fixed; top: 0; right: 0; 
        left: 0; 
        z-index: 9999; 
        background-color: #ffffff;
        padding: 15px 30px;
        height: 70px;
        border-bottom: 2px solid #e0e0e0;
        display: flex; align-items: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* FIX 1 & 2: Adjust spacing for fixed header */
    .top-bar-controls {
        left: 0;
        width: 100%;
    }
    .block-container {
        padding-top: 90px !important; 
    }
    .main .block-container {
        padding-left: 20px;
    }

    /* Target the fixed sidebar content area and give it appropriate styling */
    .stSidebar .stMarkdown {
        padding-top: 10px;
    }


    /* Input Styling in Sidebar */
    .stTextInput>div>div>input, .stDateInput>div>div>input {
        background-color: #ffffff; 
        color: #1c1c1c; 
        border: 1px solid #c0c0c0;
        border-radius: 6px;
    }
    .stButton>button {
        background-color: #1f77b4; /* Blue button */
        color: white; 
        border-radius: 6px;
    }

    /* Metric Cards (Updated for light theme contrast) */
    .metric-card {
        background: #ffffff; 
        padding: 15px 10px;
        border-radius: 8px;
        text-align: center;
        color: #1c1c1c; 
        font-weight: bold;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        border: 1px solid #e0e0e0;
        min-height: 80px; 
    }
    .metric-card b {
        font-size: 14px;
        color: #555555; 
    }
    .metric-card div {
        font-size: 20px;
        color: #1f77b4; 
    }
    .high-val {color: #2ca02c !important;} 
    .low-val {color: #d62728 !important;} 

    /* Right Panel Titles */
    .section-title {
        font-size: 20px;
        font-weight: bold;
        margin-top: 25px;
        margin-bottom: 10px;
        color: #1f77b4; 
        border-bottom: 1px solid #c0c0c0;
        padding-bottom: 5px;
    }
    /* Ensure markdown text in right panel is dark */
    .stMarkdown p, .stMarkdown strong {color: #1c1c1c !important;}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Top Control Bar (Fixed) - Title Display ---
header_placeholder = st.empty()
with header_placeholder.container():
    st.markdown(
        """
        <div class="top-bar-controls">
            <h2 style="color:#1f77b4; margin-right:30px; font-size:24px;">📈 Pro-Terminal</h2>
        </div>
        """,
        unsafe_allow_html=True
    )


# --- Data Input and Fetch Logic (SIDEBAR) ---
if 'fetch_data_clicked' not in st.session_state:
    st.session_state['fetch_data_clicked'] = False
if 'data' not in st.session_state:
    st.session_state['data'] = None

# Sidebar Content
with st.sidebar:
    st.markdown("###  Search Parameters")
    
    ticker = st.text_input("Ticker Symbol", value="INFY", key="ticker_input")
    
    default_start = datetime.now().date() - timedelta(days=365)
    start_date = st.date_input("From Date", value=default_start, key="start_date_input")
    end_date = st.date_input("To Date", value=datetime.now().date(), key="end_date_input")
    
    st.markdown("---")
    if st.button("Fetch Data", use_container_width=True):
        st.session_state['fetch_data_clicked'] = True
    else:
        pass 
    
    st.markdown("---")
    st.info("Set the date range for historical data analysis.")


# --- Data Fetch Logic (MAIN BODY) ---
if st.session_state['fetch_data_clicked']:
    
    _ticker = st.session_state.ticker_input.strip()
    
    if not _ticker:
        st.warning("Please enter a ticker symbol.")
        st.session_state['data'] = None
        st.session_state['fetch_data_clicked'] = False
        st.stop()
        
    params = {
        "symbol": _ticker, 
        "start": st.session_state.start_date_input.strftime("%Y-%m-%d"),
        "end": st.session_state.end_date_input.strftime("%Y-%m-%d")
    }
    
    try:
        with st.spinner(f"Running XGBoost and SARIMA analysis for {_ticker.upper()}..."):
            resp = requests.get(BACKEND_URL, params=params, timeout=30)
            resp.raise_for_status()
            st.session_state['data'] = resp.json()
        
        if 'error' in st.session_state['data']:
            st.error(f"Backend Analysis Error: {st.session_state['data']['error']}")
            st.session_state['data'] = None
            st.session_state['fetch_data_clicked'] = False
            st.stop()
            
    except Exception as e:
        st.error(f"Failed to fetch data or communication error: {e}")
        st.session_state['data'] = None
        st.session_state['fetch_data_clicked'] = False
        st.stop()
        
# --- Display Data (MAIN BODY) ---
if st.session_state['data']:
    data = st.session_state['data']
    chart = data.get("chart", [])
    
    # Extract prediction data
    sarima_predictions = data.get("SARIMA_Predictions", {})
    xgb_signal = data.get("XGBoost_Signal", "N/A")
    
    # Extract 3-Day and 5-Day SARIMA forecasts
    pred_3_day = sarima_predictions.get("3_Day", {})
    pred_5_day = sarima_predictions.get("5_Day", {})
    
    if not chart:
        st.info(f"No historical data available for **{st.session_state.ticker_input.upper()}** between {st.session_state.start_date_input} and {st.session_state.end_date_input}.")
        st.stop()

    # --- Extract Latest/52W Data ---
    latest = chart[-1] if chart else {}
    
    live_data = data.get("live", {})
    mock_52w_high = live_data.get("52wHigh", latest.get("High") * 1.1 if latest.get("High") else 950.00) 
    mock_52w_low = live_data.get("52wLow", latest.get("Low") * 0.8 if latest.get("Low") else 600.00)
    
    latest_metrics = {
        "date": latest.get("Date", "N/A"),
        "open": latest.get("Open"),
        "dayHigh": latest.get("High"),
        "dayLow": latest.get("Low"),
        "close": latest.get("Close"),
        "volume": latest.get("Volume"),
        "52W High": mock_52w_high,
        "52W Low": mock_52w_low,
    }

    # Format values for display
    def format_val(val, decimals=2, is_volume=False):
        if val is None: return "-"
        if is_volume: return f"{val:,.0f}"
        return f"{val:.{decimals}f}"

    # --- Live Quote Metrics ---
    st.markdown(f"## 📈 **{_ticker.upper()}** Analysis ({latest_metrics['date'][:10]})")
    
    metric_cols = st.columns(5)
    
    metric_cols[0].markdown(f"<div class='metric-card'><b>LAST PRICE</b><br><div>{format_val(latest_metrics['close'])}</div></div>", unsafe_allow_html=True)
    metric_cols[1].markdown(f"<div class='metric-card'><b>OPEN</b><br><div>{format_val(latest_metrics['open'])}</div></div>", unsafe_allow_html=True)
    metric_cols[2].markdown(f"<div class='metric-card'><b>DAY HIGH</b><br><div>{format_val(latest_metrics['dayHigh'])}</div></div>", unsafe_allow_html=True)
    metric_cols[3].markdown(f"<div class='metric-card'><b>DAY LOW</b><br><div>{format_val(latest_metrics['dayLow'])}</div></div>", unsafe_allow_html=True)
    metric_cols[4].markdown(f"<div class='metric-card'><b>VOLUME</b><br><div>{format_val(latest_metrics['volume'], is_volume=True)}</div></div>", unsafe_allow_html=True)
    
    st.markdown("---")

    # --- Layout: Chart (Left) and Indicators (Right) ---
    left, right = st.columns([4, 1.5])

    # --- Candlestick + Volume Chart ---
    with left:
        
        df = pd.DataFrame(chart)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.75, 0.25], 
            vertical_spacing=0.03
        )

        # --- Candlestick (Top) ---
        fig.add_trace(
            go.Candlestick(
                x=df["Date"],
                open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"],
                name="Price",
                increasing_line_color="#2ca02c", 
                decreasing_line_color="#d62728"
            ),
            row=1, col=1
        )
        
        # --- Add EMAs to Candlestick Chart (Row 1) ---
        # FIX: Assumes backend now correctly includes 'EMA5' and 'EMA10'
        fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA5'], line=dict(color='#1f77b4', width=1.5), name='EMA 05'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA10'], line=dict(color='#9467bd', width=1.5), name='EMA 10'), row=1, col=1)

        # --- Volume (Bottom) with Green/Red coloring ---
        colors = ["#2ca02c" if c >= o else "#d62728" for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(
            go.Bar(
                x=df["Date"], y=df["Volume"],
                marker_color=colors,
                opacity=0.7,
                name="Volume"
            ),
            row=2, col=1
        )

        # --- Layout Styling ---
        fig.update_layout(
            title=f"{_ticker.upper()} Candlestick Chart",
            height=750, 
            xaxis_rangeslider_visible=False,
            paper_bgcolor="#ffffff", 
            plot_bgcolor="#ffffff",
            font=dict(color="#1c1c1c"), 
            margin=dict(t=50, b=10, l=10, r=10),
            hovermode="x unified",
            xaxis=dict(showgrid=False),
            yaxis=dict(title="Price", showgrid=True, gridcolor="#e0e0e0"),
            yaxis2=dict(title="Volume", showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_xaxes(showgrid=False, rangeslider_visible=False)
        fig.update_yaxes(title='', showgrid=True, gridcolor='#e0e0e0')
        fig.update_yaxes(title='Price', row=1, col=1)
        fig.update_yaxes(title='Volume', row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)


    # --- Indicators / Side Panel (REVISED LAYOUT) ---
    with right:

        st.markdown('<p class="section-title">📅 52 Week Range</p>', unsafe_allow_html=True)
        st.markdown(f"**High:** <span class='high-val'>{format_val(latest_metrics['52W High'])}</span>", unsafe_allow_html=True)
        st.markdown(f"**Low:** <span class='low-val'>{format_val(latest_metrics['52W Low'])}</span>", unsafe_allow_html=True)
        
        # ----------------------------------------------
        # 1. XGBoost Signal
        # ----------------------------------------------
        st.markdown('<p class="section-title">Signal for Swing Trade (3-5 Days)</p>', unsafe_allow_html=True)
        
        if "BUY" in xgb_signal:
            st.success(f"**XGBoost:** {xgb_signal}", icon="🚀")
        elif "SELL" in xgb_signal:
            st.error(f"**XGBoost:** {xgb_signal}", icon="🔻")
        else:
            st.warning(f"**XGBoost:** {xgb_signal}", icon="🤝")
            
        
        # ----------------------------------------------
        # 2. SARIMA Predictions
        # ----------------------------------------------
        st.markdown('<p class="section-title">SARIMA Price Forecast</p>', unsafe_allow_html=True)
        
        # --- 3 Day Forecast ---
        st.markdown("**3-Day Outlook**")
        if pred_3_day.get('Predicted_Price') is not None:
            ret_3 = pred_3_day.get('Predicted_Return_%', 0)
            color = 'high-val' if ret_3 > 0 else 'low-val'
            st.markdown(f"""
                - Target Price: **{format_val(pred_3_day['Predicted_Price'])}**
                - Return: <span class='{color}'>{format_val(ret_3)}%</span>
            """, unsafe_allow_html=True)
        else:
            st.info("3-Day prediction unavailable.")
        
        
        # --- 5 Day Forecast ---
        st.markdown("**5-Day Outlook**")
        if pred_5_day.get('Predicted_Price') is not None:
            ret_5 = pred_5_day.get('Predicted_Return_%', 0)
            color = 'high-val' if ret_5 > 0 else 'low-val'
            st.markdown(f"""
                - Target Price: **{format_val(pred_5_day['Predicted_Price'])}**
                - Return: <span class='{color}'>{format_val(ret_5)}%</span>
            """, unsafe_allow_html=True)
        else:
            st.info("5-Day prediction unavailable.")

        
        # ----------------------------------------------
        # 3. Key Daily Indicators (Moved to the bottom)
        # ----------------------------------------------
        st.markdown('<p class="section-title">📊 Key Daily Indicators</p>', unsafe_allow_html=True)
        
        # Extract latest indicators using the CORRECT backend keys
        rsi_val = latest.get("RSI_D")          
        macd_formatted = format_val(latest.get("MACD_D"))
        macd_signal_formatted = format_val(latest.get("MACD_SIGNAL_D"))
        atr_val = latest.get("ATR")
        
        rsi_status = ""
        if rsi_val is not None:
            if rsi_val > 70:
                rsi_status = f"<span style='color:#d62728; font-weight:bold;'> (Overbought)</span>"
            elif rsi_val < 30:
                rsi_status = f"<span style='color:#2ca02c; font-weight:bold;'> (Oversold)</span>"
        
        st.markdown(f"**RSI (14):** {format_val(rsi_val)}{rsi_status}", unsafe_allow_html=True)
        st.markdown(f"**MACD Line:** {macd_formatted}", unsafe_allow_html=True)
        

        

       
