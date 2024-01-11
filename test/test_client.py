import tempfile
from filesender.api import FileSenderClient
from filesender.auth import UserAuth, GuestAuth
from pathlib import Path
from random import randbytes
import pytest

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

    with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".dat") as file:
        path = Path(file.name)
        # Make a 1 MB file
        file.write(randbytes(1024 ** 2))
        file.close()

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
async def test_voucher_round_trip(base_url: str, username: str, apikey: str, recipient: str):
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
        "from": username
    })

    guest_auth = GuestAuth(guest_token=guest["token"])
    guest_client = FileSenderClient(
        base_url=base_url,
        auth=guest_auth,
        threads=1
    )
    await guest_client.prepare()
    await guest_auth.prepare(guest_client.http_client)

    with tempfile.NamedTemporaryFile("wb", delete=False) as file:
        path = Path(file.name)
        # Make a 1 MB file
        file.write(randbytes(1024 ** 2))
        file.close()

        # The guest uploads the file
        transfer = await guest_client.upload_workflow(
            files=[path],
            transfer_args={
                "recipients": [username]
            }
        )
        path.unlink()
    
    with tempfile.TemporaryDirectory() as download_dir:
        # The user downloads the file
        await user_client.download_file(
            token=transfer["recipients"][0]["token"],
            file_id=transfer["files"][0]["id"],
            out_dir=Path(download_dir)
        )
        assert len(list(Path(download_dir).iterdir())) == 1
