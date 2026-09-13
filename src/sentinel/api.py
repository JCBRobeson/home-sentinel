from fastapi import FastAPI
from sentinel.core.collectors.disk import collect

app = FastAPI()

@app.get("/disk")
def disk(path: str | None = None):
    results = collect(path)
    return [r.model_dump(mode="json") for r in results]