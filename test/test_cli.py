from filesender.main import app
from typer.testing import CliRunner
import tempfile
from os import remove

runner = CliRunner()

def test_large_upload(base_url, username, apikey, recipient):
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
            "--threads", "8"
        ], catch_exceptions=False)
        if result.exit_code != 0:
            raise Exception(result.output)
        remove(file.name)
