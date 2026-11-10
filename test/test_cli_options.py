"""
Unit tests for how CLI options are turned into FileSender requests. These use a fake
client, so unlike test_cli.py they don't need a FileSender server.
"""

from filesender.main import app
from typer.testing import CliRunner
import pytest
import time
from pathlib import Path
from typing import List

runner = CliRunner()


class FakeClient:
    """
    Stands in for FileSenderClient in the CLI, and records what the CLI asks the server for
    """

    last: "FakeClient"
    #: What the CLI printed, set by invoke_with_fake_client()
    output: str = ""
    #: The recipients of the transfer that upload_workflow() returns
    recipients: List[dict] = [
        {
            "email": "recipient@example.com",
            "download_url": "http://localhost:8080/?s=download&token=abc",
        }
    ]

    def __init__(self, **kwargs: object):
        self.kwargs = kwargs
        FakeClient.last = self

    async def prepare(self) -> None:
        pass

    async def upload_workflow(self, files: List[Path], transfer_args: dict) -> dict:
        self.files = files
        self.transfer_args = transfer_args
        return {"recipients": self.recipients}

    async def create_guest(self, body: dict) -> dict:
        self.guest = body
        return {}


def invoke_with_fake_client(
    monkeypatch: pytest.MonkeyPatch, args: List[str]
) -> FakeClient:
    monkeypatch.setattr("filesender.main.FileSenderClient", FakeClient)
    result = runner.invoke(
        app,
        ["--base-url", "http://localhost:8080", *args],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    FakeClient.last.output = result.output
    return FakeClient.last


def upload_args(file: Path, *extra: str) -> List[str]:
    return [
        "upload",
        str(file),
        "--username",
        "sender@example.com",
        "--apikey",
        "abc",
        "--recipients",
        "recipient@example.com",
        *extra,
    ]


def test_upload_default_transfer_args(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """
    Without the optional arguments, the server's defaults apply, except for get_a_link,
    which is always turned off so that the recipients get an email
    """
    file = tmp_path / "file.txt"
    file.write_text("hello")
    client = invoke_with_fake_client(monkeypatch, upload_args(file))
    assert client.transfer_args == {
        "recipients": ["recipient@example.com"],
        "from": "sender@example.com",
        "options": {"email_download_complete": True, "get_a_link": False},
    }


def test_upload_transfer_args(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    file = tmp_path / "file.txt"
    file.write_text("hello")
    before = time.time()
    client = invoke_with_fake_client(
        monkeypatch,
        upload_args(
            file,
            "--subject",
            "Some subject",
            "--message",
            "Some message",
            "--days-valid",
            "7",
            "--get-a-link",
        ),
    )
    args = client.transfer_args
    assert args["subject"] == "Some subject"
    assert args["message"] == "Some message"
    assert before + 7 * 86400 - 1 <= args["expires"] <= time.time() + 7 * 86400
    assert args["options"]["get_a_link"] is True


def test_upload_days_valid_must_be_positive(tmp_path: Path):
    file = tmp_path / "file.txt"
    file.write_text("hello")
    result = runner.invoke(
        app,
        [
            "--base-url",
            "http://localhost:8080",
            *upload_args(file, "--days-valid", "0"),
        ],
    )
    assert result.exit_code != 0
    assert "not in the range" in result.output


def test_upload_prints_download_links(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """
    Every recipient's download link is printed on its own line, unwrapped, even though
    the test runner's output is narrower than the line
    """
    file = tmp_path / "file.txt"
    file.write_text("hello")
    long_token = "f13aea48-5e58-4dc3-8706-b8d84140ac5a" * 3
    monkeypatch.setattr(
        FakeClient,
        "recipients",
        [
            {
                "email": "recipient@example.com",
                "download_url": f"http://localhost:8080/?s=download&token={long_token}",
            },
            {
                "email": "other@example.com",
                "download_url": "http://localhost:8080/?s=download&token=def",
            },
        ],
    )
    client = invoke_with_fake_client(monkeypatch, upload_args(file))
    lines = client.output.splitlines()
    assert (
        f"Download link for recipient@example.com: http://localhost:8080/?s=download&token={long_token}"
        in lines
    )
    assert (
        "Download link for other@example.com: http://localhost:8080/?s=download&token=def"
        in lines
    )


def test_upload_prints_get_a_link_download_link(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """
    A link-only transfer has one recipient without an email address
    """
    file = tmp_path / "file.txt"
    file.write_text("hello")
    monkeypatch.setattr(
        FakeClient,
        "recipients",
        [{"email": "", "download_url": "http://localhost:8080/?s=download&token=abc"}],
    )
    client = invoke_with_fake_client(monkeypatch, upload_args(file, "--get-a-link"))
    assert (
        "Download link: http://localhost:8080/?s=download&token=abc"
        in client.output.splitlines()
    )


def test_invite_guest_args(monkeypatch: pytest.MonkeyPatch):
    before = time.time()
    client = invoke_with_fake_client(
        monkeypatch,
        [
            "invite",
            "guest@example.com",
            "--username",
            "sender@example.com",
            "--apikey",
            "abc",
            "--subject",
            "Please send me the files",
            "--message",
            "Thanks!",
            "--days-valid",
            "3",
        ],
    )
    guest = client.guest
    assert guest["subject"] == "Please send me the files"
    assert guest["message"] == "Thanks!"
    assert before + 3 * 86400 - 1 <= guest["expires"] <= time.time() + 3 * 86400


def test_invite_default_guest_args(monkeypatch: pytest.MonkeyPatch):
    client = invoke_with_fake_client(
        monkeypatch,
        [
            "invite",
            "guest@example.com",
            "--username",
            "sender@example.com",
            "--apikey",
            "abc",
        ],
    )
    assert "subject" not in client.guest
    assert "message" not in client.guest
    assert "expires" not in client.guest
