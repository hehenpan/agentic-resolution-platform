from fastapi import APIRouter
from app.api.v1.auth import auth_router


api_router_v1 = APIRouter()


api_router_v1.include_router(auth_router)
#api_router_v1.include_router(users_router)

