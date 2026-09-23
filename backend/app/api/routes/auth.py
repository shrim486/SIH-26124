from fastapi import APIRouter

router = APIRouter()


@router.get("/test")
def auth_test():
    return {"message": "Auth API working"}