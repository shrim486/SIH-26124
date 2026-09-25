from fastapi import APIRouter

router = APIRouter()


@router.get("/test")
def routes_test():
    return {"message": "Routes API working"}