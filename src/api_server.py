from __future__ import annotations

from typing import Any, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .draft_writer import create_draft


app = FastAPI(
    title="Draft Agent API",
    version="1.0.0",
    description="Outline and photo metadata를 블로그 초안 Markdown으로 변환하는 에이전트 API",
)


class DraftRequest(BaseModel):
    project_id: str
    outline: dict[str, Any] = Field(default_factory=dict)
    groups: List[dict[str, Any]] = Field(default_factory=list)
    hero_photos: List[dict[str, Any]] = Field(default_factory=list)
    photos: List[dict[str, Any]] = Field(default_factory=list)
    tone: Optional[str] = None
    voice_profile: Optional[dict[str, Any]] = None
    content_type: Optional[str] = None
    writing_instructions: Optional[str] = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "draft_agent"}


@app.post("/api/v1/drafts")
def create_draft_endpoint(request: DraftRequest) -> dict[str, Any]:
    draft = create_draft(request.model_dump())
    return {
        "project_id": request.project_id,
        **draft,
    }
