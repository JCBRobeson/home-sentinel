import json
import typer
from sentinel.core.logging_config import setup_logging
from sentinel.core.collectors.disk import collect

app = typer.Typer()

setup_logging()

@app.command()
def disk(path: str | None = None):
    """Print disk usage as a JSON array of CheckResults."""
    results = collect(path)
    print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))

if __name__ == "__main__":
    app()