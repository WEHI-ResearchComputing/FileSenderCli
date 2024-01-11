from dataclasses import dataclass
from typing import Any, List, Optional, Iterator, Tuple
import requests
import filesender.response_types as response
import filesender.request_types as request
from requests import Request, Response, HTTPError
from urllib.parse import urlparse, urlunparse, unquote
from filesender.auth import Auth
from shutil import copyfileobj
from pathlib import Path
from io import IOBase
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

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
        if e.request:
            raise Exception(f"Request failed with content {e.response.json()} for request {e.request.method} {e.request.url}") from e
        else:
            raise e

def yield_chunks(file: IOBase, chunk_size: int) -> Iterator[Tuple[bytes, int]]:
    """
    Yields (chunk, offset) tuples from a file, chunked by chunk_size
    """
    offset = 0
    while True:
        chunk = file.read(chunk_size)
        if not chunk:
            break
        yield chunk, offset
        offset += len(chunk)

@dataclass
class FileSenderClient:
    """
    Client that can be used to programmatically interact with FileSender
    """
    #: The base url of the file sender's API. For example https://filesender.aarnet.edu.au/rest.php
    base_url: str
    #: Size of upload chunks
    chunk_size: int
    #: Authentication provider that will be used for all privileged requests
    auth: Auth
    # Session to use for all HTTP requests
    session: requests.Session
    executor: ThreadPoolExecutor

    def __init__(
        self,
        base_url: str,
        chunk_size: Optional[int] = None,
        auth: Auth = Auth(),
        session: requests.Session = requests.Session(),
        threads: int = 1
    ):
        self.base_url = base_url
        self.auth = auth
        self.session = session
        self.executor = ThreadPoolExecutor(max_workers=threads)
        
        info = self.get_server_info()
        if chunk_size is None:
            self.chunk_size = info["upload_chunk_size"]
        elif chunk_size > info["upload_chunk_size"]:
            raise Exception(f"--chunk-size can't be greater than the server's maximum supported chunk size. For this server, the maximum is {info['upload_chunk_size']}")
        else:
            self.chunk_size = chunk_size

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
        file_info: response.File,
        body: request.FileUpdate,
    ):
        return self.sign_send(Request(
            "PUT",
            f"{self.base_url}/file/{file_info['id']}",
            params={
                "key": file_info["uid"]
            },
            json=body,
        ))

    def upload_file(
        self,
        file_info: response.File,
        file: IOBase
    ) -> None:
        """
        Uploads a file, with multiple chunks being uploaded in parallel
        """
        queue: List[Future[Response]] = []
        for chunk, offset in yield_chunks(file, self.chunk_size):
            request = self.session.prepare_request(
                self._upload_chunk_request(
                    chunk=chunk,
                    offset=offset,
                    file_info=file_info
                )
            )

            fut = self.executor.submit(self.session.send, request)
            # Keep adding to the queue until we have n jobs running
            if len(queue) < self.executor._max_workers:
                queue.append(fut)
            else:
                # Once we reach a full queue, only add new futures as previous ones finish.
                # This prevents the entire file being read into memory
                for future in as_completed(queue):
                    raise_status(future.result())
                    i = queue.index(future)
                    queue[i] = fut
                    break
        
        # Once we've submitted everything, wait for the remaining tasks to finish
        for future in as_completed(queue):
            raise_status(future.result())

    def _upload_chunk_request(
        self,
        file_info: response.File,
        offset: int,
        chunk: bytes,
    ) -> requests.Request:
        return self.auth.sign(Request(
            "PUT",
            f"{self.base_url}/file/{file_info['id']}/chunk/{offset}",
            params={
                "key": file_info["uid"]
            },
            data=chunk,
            headers={
                "Content-Type": 'application/octet-stream',
                "X-Filesender-File-Size": str(file_info["size"]),
                "X-Filesender-Chunk-Offset": str(offset),
                "X-Filesender-Chunk-Size": str(len(chunk))
            },
        ), self.session)

    def create_guest(
        self,
        body: request.Guest
    ) -> response.Guest:
        """Sends a voucher to a guest to invite them to send files"""
        return self.sign_send(Request(
            "POST",
            f"{self.base_url}/guest",
            json=body
        ))

    def download_file(
        self,
        token: str,
        file_id: int,
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

    def get_server_info(
        self
    ) -> response.ServerInfo:
        return requests.get(f"{self.base_url}/info").json()

    def upload_workflow(
        self,
        files: List[Path],
        transfer_args: request.PartialTransfer = {}
    ) -> response.Transfer:
        """
        Reusable function for uploading one or more files
        Args:
            transfer_args: Additional options to include when creating the transfer, for example a subject or message
        """
        files_by_name = {
            path.name: path for path in files
        }
        transfer = self.create_transfer({
            "files": [{
                "name": file.name,
                "size": file.stat().st_size
            } for file in files],
            "options": {
                "email_download_complete": True,
            },
            **transfer_args
        })
        self.session.params["roundtriptoken"] = transfer["roundtriptoken"]
        for file in transfer["files"]:
            with files_by_name[file["name"]].open("rb") as fp:
                # list forces the processing to occur
                self.upload_file(
                    file_info=file,
                    file=fp
                )
                self.update_file(
                    file_info=file,
                    body={"complete": True}
                )

        transfer = self.update_transfer(
            transfer_id=transfer["id"],
            body={"complete": True}
        )
        return transfer
