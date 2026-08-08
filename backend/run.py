"""启动入口：uvicorn app.main:app"""
from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app import config

    uvicorn.run(app, host=config.HOST, port=config.PORT)
