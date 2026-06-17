import sys
import importlib.util
from pathlib import Path

# Dynamiczne zaimportowanie pliku z myślnikiem w nazwie
script_path = Path(__file__).parent.parent / "alarm-scanner.py"
spec = importlib.util.spec_from_file_location("alarm_scanner", script_path)
alarm_scanner = importlib.util.module_from_spec(spec)
sys.modules["alarm_scanner"] = alarm_scanner
spec.loader.exec_module(alarm_scanner)

def test_build_cmd_no_profile():
    cmd = alarm_scanner.AWSClient._build_cmd(["ec2", "describe-regions"])
    assert cmd == ["aws", "ec2", "describe-regions"]

def test_build_cmd_with_profile():
    cmd = alarm_scanner.AWSClient._build_cmd(["ec2", "describe-regions"], profile="prod")
    assert cmd == ["aws", "--profile", "prod", "ec2", "describe-regions"]

def test_build_cmd_with_kwargs():
    cmd = alarm_scanner.AWSClient._build_cmd(["ec2", "describe-instances"], output="json")
    assert cmd == ["aws", "ec2", "describe-instances", "--output", "json"]
