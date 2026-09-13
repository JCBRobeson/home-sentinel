from fastapi import FastAPI
from sentinel.core.logging_config import setup_logging
from sentinel.core.collectors.disk import collect

app = FastAPI()

setup_logging()

@app.get("/disk")
def disk(path: str | None = None):
    results = collect(path)
    return [r.model_dump(mode="json") for r in results]