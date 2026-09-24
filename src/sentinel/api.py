from fastapi import FastAPI
from sentinel.core.logging_config import setup_logging
from sentinel.core.collectors.disk import collect as collect_disk
from sentinel.core.collectors.failed_units import collect as collect_failed_units
from sentinel.core.collectors.patch_status import collect as collect_package_updates

app = FastAPI()

setup_logging()


@app.get("/disk")
def disk(path: str | None = None):
    results = collect_disk(path)
    return [r.model_dump(mode="json") for r in results]


@app.get("/failed-units")
def failed_units():
    results = collect_failed_units()
    return [r.model_dump(mode="json") for r in results]


@app.get("/updates")
def updates():
    results = collect_package_updates()
    return [r.model_dump(mode="json") for r in results]
