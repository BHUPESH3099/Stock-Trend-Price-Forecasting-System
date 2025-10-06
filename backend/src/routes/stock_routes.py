# from fastapi import APIRouter, Query
# from ..services.stock_services import get_stock

# router = APIRouter()

# @router.get("/stock")
# def stock_endpoint(
#     symbol: str = Query(..., description="Ticker e.g., INFY, TCS"),
#     days: int = Query(120, description="Days of historical data")
# ):
#     """
#     API endpoint to get both live NSE data and historical Yahoo Finance data.
#     Returns a JSON with:
#     - symbol
#     - live: live NSE stock info
#     - chart: historical OHLCV from Yahoo Finance
#     - live_error / chart_error (if any)
#     """
#     data = get_stock(symbol.strip().upper(), days)

#     # Debug logs
#     if isinstance(data, dict):
#         print("RETURNING TO FRONTEND (keys):", list(data.keys()))
#     else:
#         print("RETURNING TO FRONTEND (raw):", data)

#     return data

from fastapi import APIRouter, Query
from ..services.stock_services import get_stock

router = APIRouter()

@router.get("/stock")
def stock_endpoint(
    symbol: str = Query(..., description="Ticker e.g., INFY, TCS"),
    days: int = Query(120, description="Days of historical data")
):
    """
    API endpoint to get live NSE + historical YFinance stock data.
    Even if one source fails, the other is returned.
    """
    data = get_stock(symbol.strip().upper(), days)
    # Optional: debug prints
    if "live" in data:
        print("LIVE DATA:", data["live"])
    if "chart" in data:
        print("HISTORICAL DATA:", data["chart"][:2])  # first 2 rows
    if "live_error" in data:
        print("LIVE ERROR:", data["live_error"])
    if "chart_error" in data:
        print("CHART ERROR:", data["chart_error"])
    return data
