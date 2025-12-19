from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from app.data import forecast_records, metrics_record

app = FastAPI(title="Forecast and Flex API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/forecast")
def forecast(
    start: str | None = Query(default=None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(default=None, description="End date YYYY-MM-DD"),
    limit: int | None = Query(default=None, ge=1, description="Max rows to return"),
) -> dict:
    try:
        rows = forecast_records(start=start, end=end, limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"count": len(rows), "data": rows}


@app.get("/metrics")
def metrics() -> dict:
    try:
        row = metrics_record()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"data": row}
