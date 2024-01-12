import tempfile
from filesender.api import FileSenderClient
from filesender.auth import UserAuth, GuestAuth
from pathlib import Path
from random import randbytes
import pytest

from filesender.request_types import GuestOptions

def test_round_trip(base_url, username, apikey, recipient):
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

    with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".dat") as file:
        path = Path(file.name)
        # Make a 1 MB file
        file.write(randbytes(1024 ** 2))
        file.close()

        # The user uploads the file
        transfer = user_client.upload_workflow(
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
        download_client.download_file(
            token=transfer["recipients"][0]["token"],
            file_id=transfer["files"][0]["id"],
            out_dir=Path(download_dir)
        )
        assert len(list(Path(download_dir).iterdir())) == 1


@pytest.mark.parametrize("guest_opts", [
    {},
    {"can_only_send_to_me": False}
])
def test_voucher_round_trip(base_url: str, username: str, apikey: str, recipient: str, guest_opts: GuestOptions):
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
    guest = user_client.create_guest({
        "recipient": recipient,
        "from": username,
        "options": guest_opts
    })

    guest_auth = GuestAuth(guest_token=guest["token"])
    guest_client = FileSenderClient(
        base_url=base_url,
        auth=guest_auth,
        threads=1
    )
    guest_auth.prepare(guest_client.session)

    with tempfile.NamedTemporaryFile("wb", delete=False) as file:
        path = Path(file.name)
        # Make a 1 MB file
        file.write(randbytes(1024 ** 2))
        file.close()

        # The guest uploads the file
        transfer = guest_client.upload_workflow(
            files=[path],
            transfer_args={
                "recipients": [username]
            }
        )
        path.unlink()
    
    with tempfile.TemporaryDirectory() as download_dir:
        # The user downloads the file
        user_client.download_file(
            token=transfer["recipients"][0]["token"],
            file_id=transfer["files"][0]["id"],
            out_dir=Path(download_dir)
        )
        assert len(list(Path(download_dir).iterdir())) == 1
