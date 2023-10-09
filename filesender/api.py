from dataclasses import dataclass
from typing import Any
import requests
import filesender.response_types as response
import filesender.request_types as request
from requests import Request, Response, HTTPError
from urllib.parse import urlparse, urlunparse, unquote
from io import IOBase
from filesender.auth import Auth
from shutil import copyfileobj
from pathlib import Path

def url_without_scheme(url: str) -> str:
    """
    Returns the URL in the appropriate format for the signature calculation, namely:
    • Without a scheme
    • Without URL encoding
    • With query parameters
    """
    return unquote(urlunparse(urlparse(url)._replace(scheme="")).lstrip("/"))

def raise_status(response: Response):
    """
    Does nothing if the response was successful.
    If it failed, throws a user friendly error
    """
    try:
        response.raise_for_status()
    except HTTPError as e:
        raise Exception(f"Request failed with content {e.response.json()}") from e

@dataclass
class FileSenderClient:
    """
    Client that can be used to programmatically interact with FileSender
    """
    #: The base url of the file sender's API. For example https://filesender.aarnet.edu.au/rest.php
    base_url: str
    #: Authentication provider that will be used for all privileged requests
    auth: Auth

    session: requests.Session = requests.Session()

    def sign_send(self, request: Request) -> Any:
        """
        Signs a request and sends it, returning the JSON result
        """
        prep = self.session.prepare_request(self.auth.sign(request, self.session))
        res = self.session.send(prep)
        raise_status(res)
        return res.json()

    def create_transfer(
        self,
        body: request.Transfer,
    ) -> response.Transfer:
        return self.sign_send(Request(
            "POST",
            f"{self.base_url}/transfer",
            json=body,
        ))

    def update_transfer(
        self,
        transfer_id: int,
        body: request.TransferUpdate,
    ) -> response.Transfer:
        return self.sign_send(Request(
            "PUT",
            f"{self.base_url}/transfer/{transfer_id}",
            json=body,
        ))

    def update_file(
        self,
        file_id: int,
        body: request.FileUpdate,
    ):
        return self.sign_send(Request(
            "PUT",
            f"{self.base_url}/file/{file_id}",
            json=body,
        ))

    def upload_chunk(
        self,
        file_id: int,
        offset: int,
        chunk: IOBase
    ) -> response.File:
        data = chunk.read()
        return self.sign_send(Request(
            "PUT",
            f"{self.base_url}/file/{file_id}/chunk/{offset}",
            data=data,
            headers={
                "Content-Type": 'application/octet-stream',
                "X-Filesender-File-Size": str(len(data)),
                "X-Filesender-Chunk-Offset": str(0),
                "X-Filesender-Chunk-Size": str(len(data))
            },
        ))
        

    def create_guest(
        self,
        body: request.Guest
    ) -> response.Guest:
        return self.sign_send(Request(
            "POST",
            f"{self.base_url}/guest",
            json=body
        ))

    def download_file(
        self,
        token: str,
        file_id: str,
        out_dir: Path
    ):
        download_endpoint = urlunparse(urlparse(self.base_url)._replace(path="/download.php"))
        res = requests.get(download_endpoint, params={
            "files_ids": file_id,
            "token": token
        }, stream=True)
        for content_param in res.headers["Content-Disposition"].split(";"):
            if "filename" in content_param:
                filename = content_param.split("=")[1].lstrip('"').rstrip('"')
                break
        else:
            raise Exception("No filename found")

        with (out_dir / filename).open("wb") as fp:
            copyfileobj(res.raw, fp)
