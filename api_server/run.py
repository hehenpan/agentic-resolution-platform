import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting server in {settings.APP_ENV.upper()} mode...")

    # Configure run parameters based on the active environment.
    # Uvicorn requires workers = 1 when reload = True. Otherwise, we use config.
    is_dev = (settings.APP_ENV == "dev")
    reload = True if is_dev else False
    workers = 1 if reload else settings.SERVER_WORKERS




    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        workers=workers,
        reload=reload
    )
