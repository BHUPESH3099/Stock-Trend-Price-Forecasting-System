import requests
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from ..config.settings import NSE_HOME, NSE_QUOTE_API, HEADERS
import ssl
import certifi
import os

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())


def fetch_live_from_nse(symbol: str):
    session = requests.Session()
    # Step 1: Get NSE homepage to retrieve cookies
    try:
        home = session.get("https://www.nseindia.com", headers=HEADERS, timeout=5, verify=certifi.where())
        home.raise_for_status()
    except requests.RequestException as e:
        print("Failed to get NSE homepage:", e)
        return {}

    # Step 2: Use session (with cookies) to get quote data
    url = NSE_QUOTE_API.format(symbol=symbol)
    try:
        response = session.get(url, headers=HEADERS, timeout=5, verify=False)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print("NSE fetch failed:", e)
        return {}



# def fetch_historical_yfinance(symbol: str, days: int = 120) -> pd.DataFrame:
#     # """Fetch historical OHLCV from Yahoo Finance"""
#     # ticker = symbol.upper() + ".NS" if not symbol.upper().endswith(".NS") else symbol
#     # end = datetime.now()
#     # start = end - timedelta(days=days + 10)
#     # df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
#     #                  end=end.strftime("%Y-%m-%d"), progress=False)
#     # if df.empty:
#     #     raise RuntimeError(f"No historical data for {ticker}")
#     # df = df.reset_index()
#     # return df

def fetch_historical_yfinance(symbol: str, days: int = 120) -> pd.DataFrame:
    """Fetch historical OHLCV from Yahoo Finance with clean columns"""
    ticker = symbol.upper() + ".NS" if not symbol.upper().endswith(".NS") else symbol
    end = datetime.now()
    start = end - timedelta(days=days + 10)

    df = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
    )

    if df.empty:
        raise RuntimeError(f"No historical data for {ticker}")

    # Reset index so Date is a column
    df = df.reset_index()

    # --- Flatten MultiIndex columns (if present) ---
    expected_cols = ["Date", "Close", "High", "Low", "Open", "Volume"]
    if df.columns.tolist() != expected_cols:
        df.columns = expected_cols

    # Ensure Date column is datetime
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    df['RSI'] = ta.rsi(df['Close'],length=14)
    df['EMA50'] = ta.ema(df['Close'], length=50)
    df['EMA200'] = ta.ema(df["Close"], length=200)
    macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    df = pd.concat([df,macd], axis=1)
    bbands = ta.bbands(df['Close'], length=20)
    df = pd.concat([df, bbands], axis=1)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    df['VMA10'] = df['Volume'].rolling(10).mean()
    df['VMA20'] = df['Volume'].rolling(20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['VMA20']
    df['OBV'] = ta.obv(df['Close'], df['Volume'])
    df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)

    df['Return'] = df['Close'].pct_change()

    df['Lag1'] = df['Return'].shift(1)
    df['Lag5'] = df['Return'].shift(5)
    df['Lag10'] = df['Return'].shift(10)
    df['Lag20'] = df['Return'].shift(20)

    df['SMA5'] = df['Close'].rolling(5).mean()
    df['SMA10'] = df['Close'].rolling(10).mean()
    df['SMA20'] = df['Close'].rolling(20).mean()

    df['Volatility10'] = df['Return'].rolling(10).std()
    df['Volatility20'] = df['Return'].rolling(20).std()

    df = df.dropna()
    print(df)

    return df


# def get_stock(symbol: str, days: int = 120) -> dict:
    """Combine live + historical stock data"""
    result = {"symbol": symbol}
    # Live NSE
    try:
        js = fetch_live_from_nse(symbol)
        price_info = js.get("priceInfo", {})
        live = {
            "open": price_info.get("open"),
            "close": price_info.get("close"),
            "lastPrice": price_info.get("lastPrice"),
            "dayHigh": price_info.get("intraDayHighLow", {}).get("max"),
            "dayLow": price_info.get("intraDayHighLow", {}).get("min"),
            "52wHigh": price_info.get("weekHighLow", {}).get("max"),
            "52wLow": price_info.get("weekHighLow", {}).get("min"),
        }
        vol = price_info.get("totalTradedVolume") or \
              js.get("securityInfo", {}).get("tradedVolume")
        live["volume"] = vol
        result["live"] = live
    except Exception as e:
        result["live_error"] = str(e)

    # Historical YFinance
    try:
        hist = fetch_historical_yfinance(symbol, days)
        hist["Date"] = pd.to_datetime(hist["Date"])
        chart = hist.tail(days).to_dict(orient="records")
        for r in chart:
            r["Date"] = r["Date"].isoformat()
        result["chart"] = chart
    except Exception as e:
        result["chart_error"] = str(e)
    print('RESULT',result)
    return result

def get_stock(symbol: str, days: int = 120) -> dict:
    """Fetch live NSE + historical YFinance data safely"""
    result = {"symbol": symbol}

    # --- 1. Fetch live NSE data ---
    try:
        js = fetch_live_from_nse(symbol)
        price_info = js.get("priceInfo", {})
        live = {
            "open": price_info.get("open"),
            "close": price_info.get("close"),
            "lastPrice": price_info.get("lastPrice"),
            "dayHigh": price_info.get("intraDayHighLow", {}).get("max"),
            "dayLow": price_info.get("intraDayHighLow", {}).get("min"),
            "52wHigh": price_info.get("weekHighLow", {}).get("max"),
            "52wLow": price_info.get("weekHighLow", {}).get("min"),
            "volume": price_info.get("totalTradedVolume") 
                      or js.get("securityInfo", {}).get("tradedVolume")
        }
        result["live"] = live
    except Exception as e:
        result["live_error"] = str(e)  # Live failed, but keep going

    # --- 2. Fetch historical YFinance data ---
    try:
        hist = fetch_historical_yfinance(symbol, days)
        hist["Date"] = pd.to_datetime(hist["Date"])
        chart = hist.tail(days).to_dict(orient="records")
        print(chart)
        for r in chart:
            r["Date"] = r["Date"].isoformat()
        result["chart"] = chart
    except Exception as e:
        result["chart_error"] = str(e)  # Chart failed
    return result
