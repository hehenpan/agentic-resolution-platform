from fastapi import APIRouter, status, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.schemas.auth import RegisterRequest, RegisterResponse, LoginRequest, LoginResponse
from app.schemas.common import BizCode
from app.api.deps import get_user_service
from app.models.models import UserType
from loguru import logger
from utils.commons import generate_sessionid
from app.core.constants import SESSION_EXPIRE_SECONDS, SESSION_COOKIE_KEY, SESSION_COOKIE_SECURE


auth_router = APIRouter()

@auth_router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(request: Request, 
        register_request: RegisterRequest,
        user_service = Depends(get_user_service),
        ):
    """
    User Registration

    Register a new user with email and password.
    """
    try:
        user_service.create_user(email=register_request.email,
                            password=register_request.password,
                            user_type=UserType.USER,
                            )
    except Exception as e:
        logger.error(f"user register error {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="Error creating user")
    
    
    return RegisterResponse(code=BizCode.SUCCESS, 
                        message="User created successfully")

    pass



@auth_router.post("/auth/login", status_code=status.HTTP_200_OK)
async def login(request: Request, 
        login_request: LoginRequest,
        user_service = Depends(get_user_service),
        ):
    """
    User Login

    Login with email and password.
    """
    try:
        result = user_service.verify_user(email=login_request.email,
                            password=login_request.password,
                            )
        if result == False:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Error logging in user")

        sessionid = user_service.create_session(email=login_request.email)



    except Exception as e:
        logger.error(f"user login error {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Error logging in user")
    
    

    # set cookie
    resp = LoginResponse(
        code=BizCode.SUCCESS, 
        message="User logged in successfully",
    )
    response = JSONResponse(
                status_code=status.HTTP_200_OK,
                content=resp.model_dump(),
            )
    response.set_cookie(
                key=SESSION_COOKIE_KEY,
                value=sessionid,
                httponly=True,
                secure=SESSION_COOKIE_SECURE,
                max_age=SESSION_EXPIRE_SECONDS,
                path="/",
            )
    
    return response

    pass



@auth_router.get("/auth/dummy", status_code=status.HTTP_200_OK)
async def auth_dummy(request: Request):
    """
    Auth Dummy

    Test auth endpoint
    """
    logger.info(f"Auth dummy endpoint hit")
    return LoginResponse(code=BizCode.SUCCESS, 
                        message="Auth dummy successfully")