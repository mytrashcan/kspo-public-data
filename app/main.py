"""FastAPI entry point for the planning-stage project."""

from typing import Annotated

from fastapi import Depends, FastAPI

from app.config import Settings, get_settings

app = FastAPI(
    title="KSPO Public Data",
    description="공공데이터 활용 경진대회 출품 준비: 기획 단계 / 스캐폴드",
)


@app.get("/")
def root() -> dict[str, str]:
    """Describe the project's current scope."""
    return {
        "project": "kspo-public-data",
        "status": "기획 단계 / 스캐폴드",
        "description": "공모전 출품 및 백엔드 포트폴리오 준비. 앱 아이디어·데이터셋 미정.",
    }


@app.get("/health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str | bool]:
    """Report local readiness without calling an external service."""
    return {"status": "ok", "data_go_kr_key_configured": settings.key_configured}
