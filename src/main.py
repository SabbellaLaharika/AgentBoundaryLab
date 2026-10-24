import os
import re
from contextlib import asynccontextmanager
from typing import List, Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from src.models import RunCreate, RunResponse, ALLOWED_STATES, SANDBOX_NAME_REGEX
from src.database import get_all_runs, insert_run, init_db
from src.config import config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB connection and schema
    try:
        init_db()
    except Exception as e:
        print(f"Startup DB init notice: {e}")
    yield

app = FastAPI(
    title="Celesto Run Ledger API",
    description="Trusted control plane API for Celesto sandbox execution runs",
    version="1.0.0",
    lifespan=lifespan
)

# Custom exception handler to return 400 instead of 422 for compliance with contract
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = "Bad request"
    if errors:
        first = errors[0]
        raw_msg = first.get("msg", "Bad request")
        if "Value error, " in raw_msg:
            msg = raw_msg.replace("Value error, ", "")
        elif "JSON decode error" in raw_msg or "json_invalid" in str(first.get("type", "")):
            msg = "Malformed JSON body"
        else:
            msg = raw_msg
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": msg}
    )

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Contract: GET /health returns 200 and {"status": "ok"}
    """
    return {"status": "ok"}

@app.get("/api/runs", response_model=List[RunResponse], status_code=status.HTTP_200_OK)
async def list_runs():
    """
    Contract: GET /api/runs returns 200 and a JSON array.
    After a fresh compose it includes sandbox name sbx-seeddemo1.
    """
    runs = get_all_runs()
    return runs

@app.post("/api/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(payload: RunCreate):
    """
    Contract: POST /api/runs with a valid body returns 201 and the stored object.
    A different execution_target, an unknown state, or a bad sandbox_name returns 400.
    """
    stored_row = insert_run({
        "run_id": payload.run_id,
        "sandbox_name": payload.sandbox_name,
        "problem_id": payload.problem_id,
        "state": payload.state,
        "execution_target": payload.execution_target
    })

    return stored_row

# Optionally serve reports if directory exists
if os.path.exists("reports"):
    app.mount("/reports", StaticFiles(directory="reports"), name="reports")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=config.API_PORT, reload=False)
