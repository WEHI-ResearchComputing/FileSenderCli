import tempfile
from filesender.api import FileSenderClient
from filesender.auth import UserAuth, GuestAuth
from pathlib import Path
import pytest
from filesender.request_types import GuestOptions
from filesender.benchmark import make_tempfile, make_tempfiles, benchmark
from unittest.mock import MagicMock, patch

def count_files_recursively(path: Path) -> int:
    """
    Returns a recursive count of the number of files within a directory. Subdirectories are not counted.
    """
    return sum([1 if child.is_file() else 0 for child in path.rglob("*")])

@pytest.mark.asyncio
async def test_round_trip(base_url: str, username: str, apikey: str, recipient: str):
    """
    This tests uploading a 1MB file, with ensures that the chunking behaviour is correct,
    but also the multithreaded uploading
    """

    user_client = FileSenderClient(
        base_url=base_url, auth=UserAuth(api_key=apikey, username=username)
    )
    await user_client.prepare()

    with make_tempfile(size=1024**2, suffix=".dat") as path:
        # The user uploads the file
        transfer = await user_client.upload_workflow(
            files=[path], transfer_args={"recipients": [recipient], "from": username}
        )

    download_client = FileSenderClient(base_url=base_url)

    with tempfile.TemporaryDirectory() as download_dir:
        # An anonymous user downloads the file
        await download_client.download_file(
            token=transfer["recipients"][0]["token"],
            file_id=transfer["files"][0]["id"],
            out_dir=Path(download_dir),
        )
        assert count_files_recursively(Path(download_dir)) == 1

    
@pytest.mark.asyncio
async def test_round_trip_dir(base_url: str, username: str, apikey: str, recipient: str):
    """
    This tests uploading two 1MB files in a directory
    """

    user_client = FileSenderClient(
        base_url=base_url, auth=UserAuth(api_key=apikey, username=username)
    )
    await user_client.prepare()

    with tempfile.TemporaryDirectory() as tempdir:
        with make_tempfiles(size=1024**2, n=2, suffix=".dat", dir = tempdir):
            # The user uploads the entire directory
            transfer = await user_client.upload_workflow(
                files=[Path(tempdir)], transfer_args={"recipients": [recipient], "from": username}
            )

    download_client = FileSenderClient(base_url=base_url)

    with tempfile.TemporaryDirectory() as download_dir:
        await download_client.download_files(
            token=transfer["recipients"][0]["token"],
            out_dir=Path(download_dir),
        )
        assert count_files_recursively(Path(download_dir)) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("guest_opts", [{}, {"can_only_send_to_me": False}])
async def test_voucher_round_trip(
    base_url: str, username: str, apikey: str, recipient: str, guest_opts: GuestOptions
):
    """
    This tests uploading a 1GB file, with ensures that the chunking behaviour is correct,
    but also the multithreaded uploading
    """
    user_client = FileSenderClient(
        base_url=base_url, auth=UserAuth(api_key=apikey, username=username)
    )

    # Invite the guest
    guest = await user_client.create_guest({
        "recipient": recipient,
        "from": username,
        "options": {
            "guest": {
                # See https://github.com/filesender/filesender/issues/1889
                "can_only_send_to_me": True
            },
        }
    })

    guest_auth = GuestAuth(guest_token=guest["token"])
    guest_client = FileSenderClient(
        base_url=base_url,
        auth=guest_auth,
    )
    await guest_client.prepare()
    await guest_auth.prepare(guest_client.http_client)

    with make_tempfile(size=1024**2, suffix=".dat") as path:
        # The guest uploads the file
        transfer = await guest_client.upload_workflow(
            files=[path],
            # FileSender will accept basically any recipients array here, but the argument can't be missing
            transfer_args={"recipients": []}
        )

    with tempfile.TemporaryDirectory() as download_dir:
        # The user downloads the file
        await user_client.download_file(
            token=transfer["recipients"][0]["token"],
            file_id=transfer["files"][0]["id"],
            out_dir=Path(download_dir),
        )
        assert count_files_recursively(Path(download_dir)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("guest_opts", [{}, {"can_only_send_to_me": False}])
async def test_guest_creation(
    base_url: str, username: str, apikey: str, recipient: str, guest_opts: GuestOptions
):
    user_client = FileSenderClient(
        base_url=base_url, auth=UserAuth(api_key=apikey, username=username)
    )

    # Invite the guest
    guest = await user_client.create_guest(
        {"recipient": recipient, "from": username, "options": {"guest": guest_opts}}
    )

    # Check that the options were acknowledged by the server
    for key, value in guest_opts.items():
        assert guest["options"][key] == value


@pytest.mark.skip("This is inconsistent")
@pytest.mark.asyncio
async def test_upload_semaphore(
    base_url: str, username: str, apikey: str, recipient: str
):
    """
    Tests that limiting the concurrency of the client increases the runtime but decreases the memory usage
    """
    with make_tempfiles(size=100_000_000, n=3) as paths:
        limited, unlimited = benchmark(paths, [1, float("inf")], [1, float("inf")], base_url, username, apikey, recipient)
    assert unlimited.time < limited.time
    assert unlimited.memory > limited.memory

@pytest.mark.asyncio
async def test_client_download_url():
    mock_http_client = MagicMock()
    token = "NOT A REAL TOKEN"
    client = FileSenderClient(base_url="http://localhost:8080")
    client.http_client = mock_http_client
    try:
        await client.download_files(token, out_dir=Path("NOT A REAL DIR"))
    except Exception:
        pass
    mock_http_client.get.assert_called_once_with("http://localhost:8080", params=dict(s="download", token=token))
