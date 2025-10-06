from pydantic import BaseModel
from typing import Optional

class StockLiveData(BaseModel):
    open: Optional[float]
    close: Optional[float]
    lastPrice: Optional[float]
    dayHigh: Optional[float]
    dayLow: Optional[float]
    volume: Optional[int]
    high52: Optional[float]
    low52: Optional[float]

class StockChartData(BaseModel):
    Date: str
    Open: float
    High: float
    Low: float
    Close: float
    Volume: int
