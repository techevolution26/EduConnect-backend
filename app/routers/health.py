from fastapi import APIRouter

router = APIRouter(tags=["Health"], prefix="/health")


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "EduConnect-api",
    }