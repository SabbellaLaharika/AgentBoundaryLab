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
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Bad request", "errors": exc.errors()}
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

@app.post("/api/runs", status_code=status.HTTP_201_CREATED)
async def create_run(request: Request):
    """
    Contract: POST /api/runs with a valid body returns 201 and the stored object.
    A different execution_target, an unknown state, or a bad sandbox_name returns 400.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Malformed JSON body"}
        )

    # Validate required fields
    required_fields = ["run_id", "sandbox_name", "problem_id", "state", "execution_target"]
    for f in required_fields:
        if f not in body or not isinstance(body[f], str):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Field '{f}' is required and must be a string"}
            )

    sandbox_name = body["sandbox_name"]
    state = body["state"]
    execution_target = body["execution_target"]

    # Contract: sandbox_name matches sbx- plus 8 or more lowercase letters or digits
    if not SANDBOX_NAME_REGEX.match(sandbox_name):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "sandbox_name must match 'sbx-' followed by 8 or more lowercase letters or digits"}
        )

    # Contract: state in allowed set
    if state not in ALLOWED_STATES:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": f"state must be one of {sorted(ALLOWED_STATES)}"}
        )

    # Contract: execution_target must be exactly 'celesto_sandbox'
    if execution_target != "celesto_sandbox":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "execution_target must be exactly 'celesto_sandbox'"}
        )

    stored_row = insert_run({
        "run_id": body["run_id"],
        "sandbox_name": sandbox_name,
        "problem_id": body["problem_id"],
        "state": state,
        "execution_target": execution_target
    })

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=stored_row
    )

# Optionally serve reports if directory exists
if os.path.exists("reports"):
    app.mount("/reports", StaticFiles(directory="reports"), name="reports")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=config.API_PORT, reload=False)
