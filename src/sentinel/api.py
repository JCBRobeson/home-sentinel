from fastapi import FastAPI
from sentinel.core.logging_config import setup_logging
from sentinel.core.collectors.disk import collect as disk_collect
from sentinel.core.collectors.failed_units import collect as failed_units_collect

app = FastAPI()

setup_logging()


@app.get("/disk")
def disk(path: str | None = None):
    results = disk_collect(path)
    return [r.model_dump(mode="json") for r in results]


@app.get("/failed-units")
def failed_units():
    results = failed_units_collect()
    return [r.model_dump(mode="json") for r in results]
