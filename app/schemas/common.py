from typing import Literal, Optional

from pydantic import BaseModel

DependencyStatus = Literal["up", "down", "configured", "unconfigured"]


class DependencyState(BaseModel):
    status: DependencyStatus
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: Literal["ok"]


class DependencyHealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    dependencies: dict[str, DependencyState]
