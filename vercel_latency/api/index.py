from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import math

app = FastAPI()

# Standard CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Force CORS headers on every response
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response

# Handle preflight requests
@app.options("/{path:path}")
async def options_handler(path: str):
    response = Response(status_code=200)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

with open(os.path.join(BASE_DIR, "q-vercel-latency.json")) as f:
    DATA = json.load(f)

def percentile95(values):
    values = sorted(values)
    n = len(values)

    if n == 1:
        return values[0]

    rank = 0.95 * (n - 1)

    lower = math.floor(rank)
    upper = math.ceil(rank)

    if lower == upper:
        return values[lower]

    frac = rank - lower
    return values[lower] + frac * (values[upper] - values[lower])

@app.get("/")
async def health():
    return {"status": "ok"}

@app.post("/")
async def metrics(payload: dict):

    threshold = payload["threshold_ms"]
    regions = payload["regions"]

    result = {}

    for region in regions:
        rows = [r for r in DATA if r["region"] == region]

        if not rows:
            result[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0
            }
            continue

        latencies = [r["latency_ms"] for r in rows]
        uptimes = [r["uptime_pct"] for r in rows]

        result[region] = {
            "avg_latency": round(sum(latencies) / len(latencies), 2),
            "p95_latency": round(percentile95(latencies), 2),
            "avg_uptime": round(sum(uptimes) / len(uptimes), 3),
            "breaches": sum(1 for x in latencies if x > threshold)
        }

    return result
