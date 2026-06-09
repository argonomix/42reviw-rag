from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.db.session import run_schema_migrations


app = FastAPI(title="ReviewRAG 42 Tokyo MVP", version="0.1.0")
app.include_router(router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def on_startup() -> None:
    run_schema_migrations()


@app.get("/")
def index() -> FileResponse:
    return FileResponse("app/static/index.html")
