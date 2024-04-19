import tempfile
from filesender.api import FileSenderClient
from filesender.auth import UserAuth, GuestAuth
from pathlib import Path
from random import randbytes
import pytest
from filesender.request_types import GuestOptions
from contextlib import contextmanager
import tracemalloc

@contextmanager
def make_tempfile(size: int, **kwargs) -> Path:
    """
    Makes a temporary binary file filled with `size` random bytes, and returns a path to it
    """
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, **kwargs) as file:
        path = Path(file.name)
        file.write(randbytes(size))
        file.close()
        yield Path(file.name)
        path.unlink()


@pytest.mark.asyncio
async def test_round_trip(base_url: str, username: str, apikey: str, recipient: str):
    """
    This tests uploading a 1MB file, with ensures that the chunking behaviour is correct,
    but also the multithreaded uploading
    """

    user_client = FileSenderClient(
        base_url=base_url,
        auth=UserAuth(
            api_key=apikey,
            username=username
        )
    )
    await user_client.prepare()

    with make_tempfile(size = 1024 ** 2, suffix=".dat") as path:
        # The user uploads the file
        transfer = await user_client.upload_workflow(
            files=[path],
            transfer_args={
                "recipients": [recipient],
                "from": username
            }
        )
        path.unlink()

    download_client = FileSenderClient(base_url=base_url)
    
    with tempfile.TemporaryDirectory() as download_dir:
        # An anonymous user downloads the file
        await download_client.download_file(
            token=transfer["recipients"][0]["token"],
            file_id=transfer["files"][0]["id"],
            out_dir=Path(download_dir)
        )
        assert len(list(Path(download_dir).iterdir())) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("guest_opts", [
    {},
    {"can_only_send_to_me": False}
])
async def test_voucher_round_trip(base_url: str, username: str, apikey: str, recipient: str, guest_opts: GuestOptions):
    """
    This tests uploading a 1GB file, with ensures that the chunking behaviour is correct,
    but also the multithreaded uploading
    """
    user_client = FileSenderClient(
        base_url=base_url,
        auth=UserAuth(
            api_key=apikey,
            username=username
        )
    )

    # Invite the guest
    guest = await user_client.create_guest({
        "recipient": recipient,
        "from": username,
        "options": {
            "guest": guest_opts
        }
    })

    guest_auth = GuestAuth(guest_token=guest["token"])
    guest_client = FileSenderClient(
        base_url=base_url,
        auth=guest_auth,
    )
    await guest_client.prepare()
    await guest_auth.prepare(guest_client.http_client)

    with make_tempfile(size = 1024 ** 2, suffix=".dat") as path:
        # The guest uploads the file
        transfer = await guest_client.upload_workflow(
            files=[path],
            transfer_args={
                "recipients": [username]
            }
        )
    
    with tempfile.TemporaryDirectory() as download_dir:
        # The user downloads the file
        await user_client.download_file(
            token=transfer["recipients"][0]["token"],
            file_id=transfer["files"][0]["id"],
            out_dir=Path(download_dir)
        )
        assert len(list(Path(download_dir).iterdir())) == 1

@pytest.mark.asyncio
@pytest.mark.parametrize("guest_opts", [
    {},
    {"can_only_send_to_me": False}
])
async def test_guest_creation(base_url: str, username: str, apikey: str, recipient: str, guest_opts: GuestOptions):
    user_client = FileSenderClient(
        base_url=base_url,
        auth=UserAuth(
            api_key=apikey,
            username=username
        )
    )

    # Invite the guest
    guest = await user_client.create_guest({
        "recipient": recipient,
        "from": username,
        "options": {
            "guest": guest_opts
        }
    })

    # Check that the options were acknowledged by the server 
    assert len(guest["options"]) == len(guest_opts)


@pytest.mark.asyncio
async def test_upload_semaphore(base_url: str, username: str, apikey: str, recipient: str):
    """
    This tests uploading a 1MB file, with ensures that the chunking behaviour is correct,
    but also the multithreaded uploading
    """

    memory = []
    with make_tempfile(size = 100_000_000) as path:
        for semaphore in [1, None]:
            client = FileSenderClient(
                base_url=base_url,
                auth=UserAuth(
                    api_key=apikey,
                    username=username
                ),
                max_concurrency=semaphore
            )
            await client.prepare()
            tracemalloc.start()
            await client.upload_workflow(
                files=[path],
                transfer_args={
                    "recipients": [recipient],
                    "from": username
                }
            )
            memory_usage = 0
            for trace in tracemalloc.take_snapshot().traces:
                memory_usage += trace.size
            memory.append(memory_usage)

    limited, unlimited = memory
    assert unlimited > 2 * limited
