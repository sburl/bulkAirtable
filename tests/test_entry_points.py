"""Regression tests for the download command entry points."""

import os
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_SCRIPT = REPOSITORY_ROOT / "bulkAirtable" / "bulkDownloadAirtable.py"
UPLOAD_SCRIPT = REPOSITORY_ROOT / "bulkAirtable" / "bulkUploadAirtable.py"
MISSING_CONFIG_MESSAGE = (
    "Error: environment variables BASE_ID, TABLE_ID, and AIRTABLE_TOKEN must be set."
)


def run_without_airtable_config(command: list[str], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run a command without credentials, so it stops before calling Airtable."""
    environment = os.environ.copy()
    for name in ("BASE_ID", "TABLE_ID", "AIRTABLE_TOKEN"):
        environment.pop(name, None)
    environment["PYTHON_DOTENV_DISABLED"] = "1"

    return subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_downloader_can_run_as_a_standalone_file(tmp_path: Path) -> None:
    """Direct execution must not fail on the downloader's relative import."""
    result = run_without_airtable_config([sys.executable, str(DOWNLOAD_SCRIPT)], tmp_path)

    assert result.returncode == 0, result.stderr
    assert MISSING_CONFIG_MESSAGE in result.stdout
    assert "attempted relative import" not in result.stderr


def test_downloader_can_run_as_a_package_module(tmp_path: Path) -> None:
    """The documented module invocation remains supported."""
    result = run_without_airtable_config(
        [sys.executable, "-m", "bulkAirtable.bulkDownloadAirtable"], tmp_path
    )

    assert result.returncode == 0, result.stderr
    assert MISSING_CONFIG_MESSAGE in result.stdout


def test_uploader_can_run_as_a_standalone_file(tmp_path: Path) -> None:
    """The uploader uses the same import fallback as the downloader."""
    result = run_without_airtable_config([sys.executable, str(UPLOAD_SCRIPT)], tmp_path)

    assert result.returncode == 0, result.stderr
    assert "Missing Airtable config variables." in result.stdout
    assert "attempted relative import" not in result.stderr
