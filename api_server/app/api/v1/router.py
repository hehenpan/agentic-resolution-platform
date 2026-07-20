from fastapi import APIRouter
from app.api.v1.auth import auth_router
from app.api.v1.files import file_router
from app.api.v1.chat import chat_router


api_router_v1 = APIRouter()


api_router_v1.include_router(auth_router)
api_router_v1.include_router(file_router)
api_router_v1.include_router(chat_router)
#api_router_v1.include_router(users_router)


