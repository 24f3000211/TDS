import time
import uuid
from collections import defaultdict, deque
import asyncio

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# =========================
# CONFIG
# =========================
ALLOWED_ORIGIN = "https://app-68xdh1.example.com"
EXAM_ORIGIN = "https://exam.sanand.workers.dev"
ALLOWED_ORIGINS = {ALLOWED_ORIGIN, EXAM_ORIGIN}

RATE_LIMIT_B = 15
RATE_LIMIT_WINDOW = 10  # seconds


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.clients = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.time()

        async with self.lock:
            q = self.clients[client_id]
            while q and now - q[0] > RATE_LIMIT_WINDOW:
                q.popleft()

            if len(q) >= RATE_LIMIT_B:
                return Response(content="Too Many Requests", status_code=429)

            q.append(now)

        return await call_next(request)


class ScopedCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        allowed = origin in ALLOWED_ORIGINS

        if request.method == "OPTIONS":
            response = Response(status_code=200 if allowed else 400)
            if allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "X-Request-ID, X-Client-Id, Content-Type"
                response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
            response.headers["Vary"] = "Origin"
            return response

        response = await call_next(request)

        if allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
        response.headers["Vary"] = "Origin"
        return response


# Order matters: last added = outermost.
# Stack (outer -> inner): CORS -> RequestContext -> RateLimiter -> app
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(ScopedCORSMiddleware)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": "24f3000211@ds.study.iitm.ac.in",
        "request_id": request.state.request_id,
    }
