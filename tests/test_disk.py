from typing import NamedTuple
import pytest
from sentinel.core.collectors import disk

class FakeUsage(NamedTuple):
    total: int
    used: int
    free: int       

def test_collect_single_path(monkeypatch: pytest.MonkeyPatch) -> None:
    
    def fake_disk_usage(path: str | None):
        return FakeUsage(total=1000, used =250, free=750)
    
    monkeypatch.setattr(disk.shutil, "disk_usage", fake_disk_usage)
    
    results = disk.collect(path="/")
    
    assert len(results) == 1
    result = results[0]
    assert result.collector == "disk_usage"
    assert result.target == "/"
    assert result.metrics["total_bytes"] == 1000
    assert result.metrics["used_bytes"] == 250
    assert result.metrics["free_bytes"] == 750
    assert result.metrics["used_percent"] == 25.0
    
def test_collect_no_path(monkeypatch: pytest.MonkeyPatch) -> None:
    
    def fake_disk_usage(path: str | None):
        raise FileNotFoundError(f"No such path: {path}")
    
    monkeypatch.setattr(disk.shutil, "disk_usage", fake_disk_usage)
    
    results = disk.collect(path="/invalid-path")
    
    assert results == [] 
    
def test_collect_default_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    
    def fake_disk_usage(path: str | None):
        return FakeUsage(total=1000, used =250, free=750)
    
    monkeypatch.setattr(disk.shutil, "disk_usage", fake_disk_usage)
    
    results = disk.collect()
    
    assert len(results) == len(disk.DEFAULT_MOUNTS)
    targets = [result.target for result in results]
    assert targets == disk.DEFAULT_MOUNTS       
