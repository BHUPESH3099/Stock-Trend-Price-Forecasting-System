from fastapi import Request
import time

async def log_request(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    print(f"{request.method} {request.url} completed in {duration:.3f}s")
    return response