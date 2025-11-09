import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
import pandas_ta as ta
import statsmodels.api as sm
import ssl, certifi, os
warnings.filterwarnings("ignore")

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())


def fetch_historical_yfinance(symbol: str, start: str, end: str) -> pd.DataFrame:
  
    ticker = symbol.upper() + ".NS" if not symbol.upper().endswith(".NS") else symbol
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")

    print(ticker)

    if (end_date - start_date).days < 365: 
        raise ValueError("Select a date range of at least 365 days") 
    
    yf_end = end_date + timedelta(days=1) 
    df = yf.download(ticker, start=start, end=yf_end, progress=False) 
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(level=1)
    df = df.reset_index()
    if 'Adj Close' in df.columns:
        df = df.drop(columns=['Adj Close'])
    
    return df


def build_indicators(df):
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)

    df.dropna(subset=['Close', 'Volume'], inplace=True)
    df = df.reset_index(drop=True)

   
    df['RSI_D'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    if macd is not None:
        df['MACD_D'] = macd.iloc[:, 0]
        df['MACD_SIGNAL_D'] = macd.iloc[:, 1]
    df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'])['ADX_14']
    stoch = ta.stoch(df['High'], df['Low'], df['Close'])
    if stoch is not None:
        df['STOCH_K'] = stoch['STOCHk_14_3_3']
        df['STOCH_D'] = stoch['STOCHd_14_3_3']
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
    df['Return'] = df['Close'].pct_change()
    df['Lag1'] = df['Return'].shift(1)
    df['Lag3'] = df['Return'].shift(3)
    df['Lag5'] = df['Return'].shift(5)
    df['Volatility10'] = df['Return'].rolling(10).std()
    df['Volatility05'] = df['Return'].rolling(5).std()
    df['EMA5'] = df['Close'].ewm(span=5).mean()
    df['EMA10'] = df['Close'].ewm(span=10).mean()

  
    df['Week'] = df['Date'].dt.to_period('W')
    df['Month'] = df['Date'].dt.to_period('M')


    
    df_w = df.resample('W', on='Date').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna() # Drop any incomplete weekly periods
    macd_w = ta.macd(df_w['Close']) 
    df_w['MACD_W'] = macd_w.iloc[:, 0]
    df_w['MACD_SIGNAL_W'] = macd_w.iloc[:, 1]
    df_w['RSI_W'] = ta.rsi(df_w['Close'], 14)
    df_w['Week'] = df_w.index.to_period('W') # Use the index period for merging

    
    df_m = df.resample('M', on='Date').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna() 
    macd_m = ta.macd(df_m['Close'], fast=6, slow=13, signal=5) 
    df_m['MACD_M'] = macd_m.iloc[:, 0]
    df_m['MACD_SIGNAL_M'] = macd_m.iloc[:, 1]
    df_m['RSI_M'] = ta.rsi(df_m['Close'], 14)
    df_m['Month'] = df_m.index.to_period('M') 

   
    df = df.merge(df_w[['Week','RSI_W','MACD_W','MACD_SIGNAL_W']], on='Week', how='left')
    df = df.merge(df_m[['Month','RSI_M','MACD_M','MACD_SIGNAL_M']], on='Month', how='left')

    # ---------------- Drop helper columns & fill NaNs ----------------
    df.drop(columns=['Week','Month'], inplace=True)
    
    df.fillna(method='bfill', inplace=True) 
    df.fillna(method='ffill', inplace=True) 
    df = df.reset_index(drop=True)

    
    return df

def generate_xgboost_signal(df):
    """
    Generates a trading signal using an XGBoost classifier, 
    adopting the signal and model training/evaluation logic 
    from the second code snippet.
    """
    
    df['Future_Max'] = df['Close'].shift(-3).rolling(3).max()
    df['Future_Min'] = df['Close'].shift(-3).rolling(3).min()
    future_return = (df['Future_Max'] - df['Close']) / df['Close']
    future_loss = (df['Future_Min'] - df['Close']) / df['Close']
    # Signal: 1 (Buy) if a 2% gain is possible, -1 (Sell) if a 2% loss is possible, 0 (Hold) otherwise
    df['Signal'] = np.where(future_return > 0.02, 1, np.where(future_loss < -0.02, -1, 0))
    
   
    features = [
        'RSI_D','MACD_D','MACD_SIGNAL_D','STOCH_K','STOCH_D','ADX',
        'MFI','ATR','Volatility05','Volatility10','EMA5','EMA10','Lag1','Lag3','Lag5',
        'RSI_W','MACD_W','MACD_SIGNAL_W','RSI_M','MACD_M','MACD_SIGNAL_M'
    ]

   
    weekly_monthly = ['RSI_W','MACD_W','MACD_SIGNAL_W','RSI_M','MACD_M','MACD_SIGNAL_M']
    df[weekly_monthly] = df[weekly_monthly].fillna(method='bfill').fillna(method='ffill')

    
    df[features] = df[features].apply(pd.to_numeric, errors='coerce')

   
    df = df.dropna(subset=features + ['Signal']).reset_index(drop=True)
    

   
    X = df[features].to_numpy()
    y = df['Signal'].to_numpy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_res, y_res = SMOTE().fit_resample(X_scaled, y)

    split = int(len(X_res)*0.8)
    X_train, X_test = X_res[:split], X_res[split:]
    y_train, y_test = y_res[:split], y_res[split:]

    
    model = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss')
    # Shift labels to non-negative for XGBoost: -1->0, 0->1, 1->2
    y_train_xgb = y_train + 1
    y_test_xgb = y_test + 1

    model.fit(X_train, y_train_xgb)
    

    pred = model.predict(X_test) - 1
    
   
    latest_features = X_scaled[-1].reshape(1, -1)
    latest_pred = model.predict(latest_features)[0] - 1
    
    acc = accuracy_score(y_test, pred)
    signal_map = {1: "BUY 📈", 0: "HOLD 🤝", -1: "SELL 📉"}
    signal = signal_map.get(latest_pred, "UNKNOWN")
    
    return signal


def predict_with_sarima(df):
    
    results = {}
    latest_close = df['Close'].iloc[-1]
    for horizon in [3, 5]:
        sarima_model = sm.tsa.statespace.SARIMAX(
            df['Close'],
            order=(2,1,2),
            seasonal_order=(1,1,1,12),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        sarima_result = sarima_model.fit(disp=False)
        forecast = sarima_result.forecast(steps=horizon)
        predicted_price = forecast.iloc[-1]
        
        
        pred_return = ((predicted_price - latest_close) / latest_close) * 100
        error_pct = abs(predicted_price - latest_close) / latest_close * 100 
        results[f"{horizon}_Day"] = {
            "Predicted_Price": round(predicted_price, 2),
            "Latest_Close": round(latest_close, 2),
            "Predicted_Return_%": round(pred_return, 2),
            # Renaming to 'Predicted_Deviation_%' for clarity on current data
            "Predicted_Deviation_%": round(error_pct, 2), 
            "AIC": round(sarima_result.aic, 2),
            "BIC": round(sarima_result.bic, 2)
        }
   
    return results


def get_stock(symbol: str, start: str = None, end: str = None) -> dict:
    """
    Main function to fetch stock data, build indicators, run XGBoost signal,
    and get SARIMA predictions.
    """
    result = {"symbol": symbol}
    try:
        
        hist = fetch_historical_yfinance(symbol, start, end)
        
      
        hist = build_indicators(hist)
        
        
        xgb_result = generate_xgboost_signal(hist.copy()) 
        
       
        sarima_result = predict_with_sarima(hist.copy())

       
        hist["Date"] = pd.to_datetime(hist["Date"])
        
        
        chart_columns = [
            'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 
            'RSI_D', 'MACD_D', 'MACD_SIGNAL_D', 'ATR', 'EMA5', 'EMA10'
        ]
        
        
        chart_data = hist[chart_columns]
        
        
        chart = chart_data.to_dict(orient="records") 
        
        for r in chart:
            r["Date"] = r["Date"].isoformat()

        
        result["chart"] = chart
        result["XGBoost_Signal"] = xgb_result
        result["SARIMA_Predictions"] = sarima_result
        
        
    except Exception as e:
        result["error"] = str(e)
        print(f"An error occurred: {e}")


    return result

