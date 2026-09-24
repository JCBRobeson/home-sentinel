import json
import typer
from sentinel.core.logging_config import setup_logging
from sentinel.core.collectors.disk import collect as collect_disk
from sentinel.core.collectors.failed_units import collect as collect_failed_units
from sentinel.core.collectors.patch_status import collect as collect_package_updates

app = typer.Typer()

setup_logging()


@app.command()
def disk(path: str | None = None):
    """Print disk usage as a JSON array of CheckResults."""
    results = collect_disk(path)
    print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))


@app.command()
def failed_units():
    """Print failed units as a JSON array of CheckResults"""
    results = collect_failed_units()
    print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))


@app.command()
def updates():
    """Collect package updates from dnf as a JSON array of CheckResults"""
    results = collect_package_updates()
    print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))


if __name__ == "__main__":
    app()
