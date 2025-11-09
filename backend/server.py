from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.src.routes import stock_routes
from backend.src.middleware.custom_middleware import log_request


app = FastAPI(title="Stock API")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(log_request)

# Include the stock route
app.include_router(stock_routes.router)


