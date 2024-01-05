from typing import List, Optional, Set
from typing_extensions import Annotated
from bs4 import BeautifulSoup

import requests
from filesender.api import FileSenderClient
from typer import Typer, Option, Argument, Context
from rich import print
from pathlib import Path
from filesender.auth import Auth, UserAuth, GuestAuth
from filesender.config import get_defaults

ChunkSize = Annotated[Optional[int], Option(help="The size of each chunk to read from the input file during the upload process. Larger values will result in a faster upload but use more memory. If the value exceeds the server's maximum chunk size, this command will fail.")]
Threads = Annotated[int, Option(help="The maximum number of threads to use for concurrently uploading files")]
Verbose = Annotated[bool, Option(help="Enable more detailed outputs")]
Delay = Annotated[int, Option(help="Delay the signature timestamp by N seconds. Increase this value if you have a slow connection. This value should be approximately the time it takes you to upload one chunk to the server.", metavar="N")]

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
    context: Context,
    verbose: Annotated[bool, Argument(help="Enable more detailed outputs")] = False,
    delay: Delay = 0
):
    """
    Invites a user to send files to you
    """
    client = FileSenderClient(
        auth=UserAuth(
            api_key=apikey,
            username=username,
            delay=delay
        ),
        base_url=context.obj["base_url"]
    )
    result = client.create_guest({
        "from": username,
        "recipient": recipient,
        "options": {
            "guest": {
                "can_only_send_to_me": True,
            }
        }
    })
    if verbose:
        print(result)
    print("Invitation successfully sent")

@app.command(context_settings=context)
def upload_voucher(
    files: Annotated[List[Path], Argument(file_okay=True, dir_okay=False, resolve_path=True, exists=True, help="Files to upload")],
    guest_token: Annotated[str, Option(help="The guest token. This is the part of the upload URL after 'vid='")],
    email: Annotated[str, Option(help="The email address that was invited to upload files")],
    context: Context,
    threads: Threads = 1,
    chunk_size: ChunkSize = None,
    verbose: Verbose = False
):
    """
    Uploads files to a voucher that you have been invited to
    """
    auth = GuestAuth(guest_token=guest_token)
    client = FileSenderClient(
        auth=auth,
        base_url=context.obj["base_url"],
        chunk_size = chunk_size,
        threads=threads
    )
    auth.prepare(client.session)
    result = client.upload_workflow(files, {"from": email, "recipients": []})
    if verbose:
        print(result)
    print("Upload completed successfully")

@app.command(context_settings=context)
def upload(
    username: Annotated[str, Option(help="Username of the user performing the upload")],
    apikey: Annotated[str, Option(help="API token of the user performing the upload")],
    files: Annotated[List[Path], Argument(file_okay=True, dir_okay=False, resolve_path=True, exists=True, help="Files to upload")],
    recipients: Annotated[List[str], Option(show_default=False, help="One or more email addresses to send the files")],
    context: Context,
    threads: Threads = 1,
    verbose: Verbose = False,
    chunk_size: ChunkSize = None,
    delay: Delay = 0
):
    """
    Sends files to an email of choice
    """
    client = FileSenderClient(
        auth=UserAuth(
            api_key=apikey,
            username=username,
            delay=delay
        ),
        base_url=context.obj["base_url"],
        threads=threads,
        chunk_size=chunk_size
    )
    result = client.upload_workflow(files, {"recipients": recipients, "from": username})
    if verbose:
        print(result)
    print("Upload completed successfully")

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
        base_url=context.obj["base_url"],
        threads=threads
    )
    for file in files_from_token(token, client.session):
        client.executor.submit(
            client.download_file,
            token=token,
            file_id=file,
            out_dir=out_dir
        )
    print(f"Download completed successfully. Files can be found in {out_dir}")

def files_from_token(token: str, session: requests.Session) -> Set[int]:
    download_page = session.get(
        "https://filesender.aarnet.edu.au",
        params = {
            "s": "download",
            "token": token
        }
    )
    files = set()
    for file in BeautifulSoup(download_page.content, "html.parser").find_all(class_="file"):
        files.add(int(file.attrs["data-id"]))
    return files

if __name__ == "__main__":
    app()
