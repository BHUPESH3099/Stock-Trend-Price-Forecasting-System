from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# Root endpoint to avoid 404 at "/"
@app.get("/")
def root():
    return {"message": "Stock API is running. Use /stock?symbol=INFY endpoint to get data."}

# Global exception handler to catch unexpected errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": str(exc)},
    )
