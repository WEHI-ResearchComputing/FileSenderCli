from filesender.main import app
from typer.testing import CliRunner
import tempfile
from os import remove
import pytest
from typing import List

runner = CliRunner()

@pytest.mark.parametrize("guest_opts", [
    ["--no-one-time"],
    ["--no-only-to-me"],
])
def test_guest_params(base_url: str, username: str, apikey: str, recipient: str, delay: int, guest_opts: List[str]):
    """
    This tests configuring some guest options using the CLI
    """
    with tempfile.NamedTemporaryFile("wb", delete=False) as file:
        # Make a 1 MB file
        file.truncate(1024)
        file.close()
        result = runner.invoke(app, [
            "--base-url", base_url,
            "invite",
            recipient,
            "--username", username,
            "--apikey", apikey,
            "--delay", str(delay),
            *guest_opts
        ], catch_exceptions=False)
        if result.exit_code != 0:
            raise Exception(result.output)
        remove(file.name)


def test_large_upload(base_url: str, username: str, apikey: str, recipient: str, delay: int):
    """
    This tests uploading a 1GB file, with ensures that the chunking behaviour is correct,
    but also the multithreaded uploading
    """
    with tempfile.NamedTemporaryFile("wb", delete=False) as file:
        # Make a 1 GB file
        file.truncate(1024 ** 3)
        file.close()
        result = runner.invoke(app, [
            "--base-url", base_url,
            "upload",
            file.name,
            "--username", username,
            "--apikey", apikey,
            "--recipients", recipient,
            "--delay", str(delay),
        ], catch_exceptions=False)
        if result.exit_code != 0:
            raise Exception(result.output)
        remove(file.name)
