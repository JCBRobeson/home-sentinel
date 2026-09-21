import json
import typer
from sentinel.core.logging_config import setup_logging
from sentinel.core.collectors.disk import collect as disk_collect
from sentinel.core.collectors.failed_units import collect as failed_units_collect

app = typer.Typer()

setup_logging()

@app.command()
def disk(path: str | None = None):
    """Print disk usage as a JSON array of CheckResults."""
    results = disk_collect(path)
    print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))

@app.command()
def failed_units():
    """Print failed units as a JSON array of CheckResults"""
    results = failed_units_collect()
    print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
    

if __name__ == "__main__":
    app()