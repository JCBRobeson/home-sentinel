import pytest
from subprocess import CompletedProcess
from sentinel.core.collectors import failed_units

    

def test_failed_units_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    
    failed_target_string = "sentinel-test-fail"
    
    def fake_subprocess_run(args: list[str], capture_output:bool, text:bool):
        return CompletedProcess(args=["systemctl", "list-units", "-t", "service", "--state=failed","--no-legend", "--plain"], returncode=0, stdout=("%s2.service loaded failed failed [systemd-run] /bin/false\n%s.service  loaded failed failed [systemd-run] /bin/false", failed_target_string, failed_target_string), stderr="")
    
    monkeypatch.setattr(failed_units.subprocess, "run", fake_subprocess_run)
    
    results = failed_units.collect()
    assert len(results) == 2
    
    result1, result2 = results
    assert result1.target is not None and result2.target is not None
    assert failed_target_string in result1.target and failed_target_string in result2.target
    assert result1.metrics["failed"] == True and result2.metrics["failed"] == True
    
def test_failed_units_command_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    
    def fake_subprocess_run(args: list[str], capture_output:bool, text:bool):
            raise FileNotFoundError
    
    monkeypatch.setattr(failed_units.subprocess, "run", fake_subprocess_run)
    
    results = failed_units.collect()    
    assert len(results) == 0  

def test_failed_units_nonsuccess_code(monkeypatch: pytest.MonkeyPatch) -> None:
    
    def fake_subprocess_run(args: list[str], capture_output:bool, text:bool):
                return CompletedProcess(args=["dummy", "command"], returncode=1, stdout="", stderr="dummy command not found")
            
    monkeypatch.setattr(failed_units.subprocess, "run", fake_subprocess_run)
            
    results = failed_units.collect()  
    assert len(results) == 0
        
def test_failed_units_malformed_string(monkeypatch: pytest.MonkeyPatch) -> None:
    
    def fake_subprocess_run(args: list[str], capture_output:bool, text:bool):
            return CompletedProcess(args=["systemctl", "list-units", "-t", "service", "--state=failed","--no-legend", "--plain"], returncode=0, stdout="sentinel-test-fail2.service loaded failed failed [systemd-run] /bin/false\nsentinel-test-fail.service  loaded failed failed", stderr="")
        
    monkeypatch.setattr(failed_units.subprocess, "run", fake_subprocess_run)
        
    results = failed_units.collect()
    assert len(results) == 1   