from fastapi import APIRouter

router = APIRouter()


@router.get("/test")
def traffic_test():
    return {"message": "Traffic API working"}