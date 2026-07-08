from starlette_context.plugins import RequestIdPlugin
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import status
from starlette_context import context
from sqlmodel import Session
from app.models.engines import engine as default_engine
from app.services.user_service import UserService
from app.core.constants import SESSION_INFO_KEY, SESSION_COOKIE_KEY
from loguru import logger

# Configure the starlette-context plugins
context_plugins = (
    RequestIdPlugin(
        force_new_uuid=False,  
        validate=False,        
    ),
)

def safe_get_context(key, default=None):
    # Check if the current context exists first
    if context.exists():
        return context.get(key, default)
    return default


def safe_set_context(key, value):
    if context.exists():
        context[key] = value
    else:
        logger.error(f"not in context when set key:{key} value:{value}")



def safe_url_path_for(app, name: str) -> str:
    
    try:
        return str(app.url_path_for(name))
    except Exception:
        return ""

class VerifySessionidMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"VerifySessionidMiddleware  called, path={request.url.path} method:{request.method}")
        
        # Resolve paths dynamically using route names (equivalent to Django reverse)
        register_path = safe_url_path_for(request.app, "register")
        login_path = safe_url_path_for(request.app, "login")
        test_context_path = safe_url_path_for(request.app, "read_starlette_context")

        if request.method == 'POST' and request.url.path == register_path:
            response = await call_next(request)
            return response

        if request.method == 'POST' and request.url.path == login_path:
            response = await call_next(request)
            return response

        #for context test, url white list
        if request.url.path == test_context_path:
            response = await call_next(request)
            return response



        sessionid = request.cookies.get(SESSION_COOKIE_KEY)
        logger.info(f"sessionid:{sessionid}")
        if sessionid is None:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content="need auth",
            )
        db_engine = getattr(request.app.state, "db_engine", default_engine)
        with Session(db_engine) as dbsession:
            user_services = UserService(dbsession=dbsession)
            sessioninfo = user_services.get_session_info(sessionid=sessionid)
            if sessioninfo is None:
                logger.error(f"invalid sessionid:{sessionid}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            logger.info(f"sessionid check success, sessionid:{sessionid}, email:{sessioninfo.email}")

            request.state.sessioninfo = sessioninfo
            
        safe_set_context(SESSION_INFO_KEY, sessioninfo)
        
        response = await call_next(request)
        return response    


        
           