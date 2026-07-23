import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting server in {settings.APP_ENV.upper()} mode...")

    # Uvicorn requires workers = 1 when reload = True. Otherwise, we use config.
    workers = 1 if settings.SERVER_RELOAD else settings.SERVER_WORKERS

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        workers=workers,
        reload=settings.SERVER_RELOAD,
        reload_dirs=settings.SERVER_RELOAD_DIRS or None,
    )
