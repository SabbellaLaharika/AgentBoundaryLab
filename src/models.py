import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

ALLOWED_STATES = {"created", "ready", "running", "succeeded", "failed", "deleted"}
SANDBOX_NAME_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")

class RunCreate(BaseModel):
    run_id: str = Field(..., min_length=1)
    sandbox_name: str
    problem_id: str = Field(..., min_length=1)
    state: str
    execution_target: str

    @field_validator("sandbox_name")
    def validate_sandbox_name(cls, v: str) -> str:
        if not SANDBOX_NAME_REGEX.match(v):
            raise ValueError("sandbox_name must start with 'sbx-' followed by 8 or more lowercase letters or digits")
        return v

    @field_validator("state")
    def validate_state(cls, v: str) -> str:
        if v not in ALLOWED_STATES:
            raise ValueError(f"state must be one of {sorted(ALLOWED_STATES)}")
        return v

    @field_validator("execution_target")
    def validate_execution_target(cls, v: str) -> str:
        if v != "celesto_sandbox":
            raise ValueError("execution_target must be exactly 'celesto_sandbox'")
        return v

class RunResponse(BaseModel):
    run_id: str
    sandbox_name: str
    problem_id: str
    state: str
    execution_target: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
