import json
import typer
from sentinel.core.collectors.linux import get_disk_usage

app = typer.Typer()

@app.command()
def disk(path: str = "/"):
    """Print disk usage for PATH as JSON."""
    result = get_disk_usage(path)
    print(json.dumps(result, indent=2))
    
if __name__ == "__main__":
    app()