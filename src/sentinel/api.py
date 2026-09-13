from fastapi import FastAPI
from sentinel.core.collectors.linux import get_disk_usage

app = FastAPI()

@app.get("/disk")
def disk(path: str = "/"):
    return get_disk_usage(path)