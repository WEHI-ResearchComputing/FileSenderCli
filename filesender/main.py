from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Set, cast
from typing_extensions import Annotated
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup

import requests
from filesender.api import FileSenderClient
from typer import Typer, Option, Argument, Context
from rich import print
from pathlib import Path
from configparser import ConfigParser
from filesender.auth import Auth, UserAuth, GuestAuth
from filesender.request_types import PartialTransfer

def get_defaults() -> dict:
    defaults = {}
    path = Path.home() / ".filesender" / "filesender.py.ini"
    if path.exists():
        parser = ConfigParser()
        parser.read(path)
        if parser.has_option("system", "base_url"):
            defaults["base_url"] = parser.get("system", "base_url")
        if parser.has_option("system", "default_transfer_days_valid"):
            defaults["default_transfer_days_valid"] = parser.get("system", "default_transfer_days_valid")
        if parser.has_option("user", "username"):
            defaults["username"] = parser.get("user", "username")
        if parser.has_option("user", "apikey"):
            defaults["apikey"] = parser.get("user", "apikey")

    return defaults

context = {
    "default_map": get_defaults()
}
app = Typer(name="filesender")


@app.callback(context_settings=context)
def common_args(
    base_url: Annotated[str, Option(help="The URL of the FileSender REST API")],
    context: Context
):
    context.obj = {
        "base_url": base_url
    }

@app.command(context_settings=context)
def invite(
    username: Annotated[str, Option(help="Your username. This is the username of the person doing the inviting, not the person being invited.")],
    apikey: Annotated[str, Option(help="Your API token. This is the token of the person doing the inviting, not the person being invited.")],
    recipient: Annotated[str, Argument(help="The email address of the person to invite")],
    context: Context
):
    """
    Invites a user to send files to you
    """
    client = FileSenderClient(
        auth=UserAuth(
            api_key=apikey,
            username=username
        ),
        base_url=context.obj["base_url"]
    )
    print(client.create_guest({
        "from": username,
        "recipient": recipient
    }))

@app.command(context_settings=context)
def upload_voucher(
    files: Annotated[List[Path], Argument(file_okay=True, dir_okay=False, resolve_path=True, exists=True, help="Files to upload")],
    guest_token: Annotated[str, Option(help="The guest token. This is the part of the upload URL after 'vid='")],
    email: Annotated[str, Option(help="The email address that was invited to upload files")],
    context: Context
):
    """
    Uploads files to a voucher that you have been invited to
    """
    auth = GuestAuth(guest_token=guest_token)
    client = FileSenderClient(
        auth=auth,
        base_url=context.obj["base_url"]
    )
    auth.prepare(client.session)
    upload_workflow(client, files, {"from": email, "recipients": []})

@app.command(context_settings=context)
def upload(
    username: Annotated[str, Option(help="Username of the user performing the upload")],
    apikey: Annotated[str, Option(help="API token of the user performing the upload")],
    files: Annotated[List[Path], Argument(file_okay=True, dir_okay=False, resolve_path=True, exists=True, help="Files to upload")],
    recipients: Annotated[List[str], Option(show_default=False, help="One or more email addresses to send the files")],
    context: Context
):
    """
    Sends files to an email of choice
    """
    client = FileSenderClient(
        auth=UserAuth(
            api_key=apikey,
            username=username
        ),
        base_url=context.obj["base_url"]
    )
    upload_workflow(client, files, {"recipients": recipients, "from": username})

def upload_workflow(
    client: FileSenderClient,
    files: List[Path],
    transfer_args: PartialTransfer
):
    """
    Reusable function for uploading one or more files
    Args:
        transfer_args: Additional options to include when creating the transfer, for example a subject or message
    """
    files_by_name = {
        path.name: path for path in files
    }
    transfer = client.create_transfer({
        "files": [{
            "name": file.name,
            "size": file.stat().st_size
        } for file in files],
        "options": {
            "email_download_complete": True,
        },
        **transfer_args
    })
    client.session.params["roundtriptoken"] = transfer["roundtriptoken"]
    for file in transfer["files"]:
        with files_by_name[file["name"]].open("rb") as fp:
            client.upload_chunk(
                file_id=file["id"],
                chunk=fp,
                offset=0
            )
            client.update_file(
                file_id=file["id"],
                body={"complete": True}
            )

    transfer = client.update_transfer(
        transfer_id=transfer["id"],
        body={"complete": True}
    )
    print(transfer)

@app.command(context_settings=context)
def download(
    context: Context,
    token: Annotated[str, Argument(help='The part of the download URL after "token="')],
    out_dir: Annotated[Path, Option(dir_okay=True, file_okay=False, exists=True, help="Path to the directory to store the output files")] = Path.cwd(),
    threads: Annotated[int, Option(help="Maximum number of threads to use to download the files concurrently")] = 1
):
    """Downloads all files associated with a transfer"""
    client = FileSenderClient(
        auth=Auth(),
        base_url=context.obj["base_url"]
    )
    with ThreadPoolExecutor(max_workers=threads) as executor:
        for file in files_from_token(token, client.session):
            executor.submit(
                client.download_file,
                token=token,
                file_id=file,
                out_dir=out_dir
            )

def files_from_token(token: str, session: requests.Session) -> Set[str]:
    download_page = session.get(
        "https://filesender.aarnet.edu.au",
        params = {
            "s": "download",
            "token": token
        }
    )
    files = set()
    for file in BeautifulSoup(download_page.content, "html.parser").find_all(class_="file"):
        files.add(file.attrs["data-id"])
    return files

if __name__ == "__main__":
    app()
