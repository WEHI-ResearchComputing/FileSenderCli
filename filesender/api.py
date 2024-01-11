from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, AsyncIterator

from bs4 import BeautifulSoup
import filesender.response_types as response
import filesender.request_types as request
from urllib.parse import urlparse, urlunparse, unquote
from filesender.auth import Auth
from pathlib import Path
from httpx import Request, Response, AsyncClient, HTTPStatusError
from asyncio import TaskGroup
import aiofiles

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
    except HTTPStatusError as e:
        if e.request:
            raise Exception(f"Request failed with content {e.response.json()} for request {e.request.method} {e.request.url}") from e
        else:
            raise e

async def yield_chunks(path: Path, chunk_size: int) -> AsyncIterator[Tuple[bytes, int]]:
    """
    Yields (chunk, offset) tuples from a file, chunked by chunk_size
    """
    async with aiofiles.open(path, "rb") as fp:
        offset = 0
        while True:
            chunk = await fp.read(chunk_size)
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
    chunk_size: Optional[int]
    #: Authentication provider that will be used for all privileged requests
    auth: Auth
    # Session to use for all HTTP requests
    http_client: AsyncClient

    def __init__(
        self,
        base_url: str,
        chunk_size: Optional[int] = None,
        auth: Auth = Auth(),
        threads: int = 1
    ):
        self.base_url = base_url
        self.auth = auth
        self.http_client = AsyncClient()
        self.chunk_size = chunk_size

    async def prepare(self):
        """
        Checks that the chunk size is appropriate and/or sets the chunk size based on the server info
        """
        info = await self.get_server_info()
        if self.chunk_size is None:
            self.chunk_size = info["upload_chunk_size"]
        elif self.chunk_size > info["upload_chunk_size"]:
            raise Exception(f"--chunk-size can't be greater than the server's maximum supported chunk size. For this server, the maximum is {info['upload_chunk_size']}")

    async def sign_send(self, request: Request) -> Any:
        """
        Signs a request and sends it, returning the JSON result
        """
        self.auth.sign(request, self.http_client)
        res = await self.http_client.send(request)
        raise_status(res)
        return res.json()

    async def create_transfer(
        self,
        body: request.Transfer,
    ) -> response.Transfer:
        return await self.sign_send(self.http_client.build_request(
            "POST",
            f"{self.base_url}/transfer",
            json=body,
        ))

    async def update_transfer(
        self,
        transfer_id: int,
        body: request.TransferUpdate,
    ) -> response.Transfer:
        return await self.sign_send(self.http_client.build_request(
            "PUT",
            f"{self.base_url}/transfer/{transfer_id}",
            json=body,
        ))

    async def update_file(
        self,
        file_info: response.File,
        body: request.FileUpdate,
    ) -> Any:
        return await self.sign_send(self.http_client.build_request(
            "PUT",
            f"{self.base_url}/file/{file_info['id']}",
            params={
                "key": file_info["uid"]
            },
            json=body,
        ))

    async def upload_file(
        self,
        file_info: response.File,
        path: Path
    ) -> None:
        """
        Uploads a file, with multiple chunks being uploaded in parallel
        """
        if self.chunk_size is None:
            raise Exception(".prepare() has not been called!")

        # Upload each chunk concurrently
        async with TaskGroup() as tg:
            async for chunk, offset in yield_chunks(path, self.chunk_size):
                tg.create_task(
                    self._upload_chunk(
                        chunk=chunk,
                        offset=offset,
                        file_info=file_info
                    )
                )

    async def _upload_chunk(
        self,
        file_info: response.File,
        offset: int,
        chunk: bytes,
    ) -> Request:
        return await self.sign_send(self.http_client.build_request(
            "PUT",
            f"{self.base_url}/file/{file_info['id']}/chunk/{offset}",
            params={
                "key": file_info["uid"]
            },
            content=chunk,
            headers={
                "Content-Type": 'application/octet-stream',
                "X-Filesender-File-Size": str(file_info["size"]),
                "X-Filesender-Chunk-Offset": str(offset),
                "X-Filesender-Chunk-Size": str(len(chunk))
            },
        ))

    async def create_guest(
        self,
        body: request.Guest
    ) -> response.Guest:
        return await self.sign_send(self.http_client.build_request(
            "POST",
            f"{self.base_url}/guest",
            json=body
        ))

    async def files_from_token(self, token: str) -> set[int]:
        download_page = await self.http_client.get(
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

    async def download_files(
        self,
        token: str,
        out_dir: Path
    ):
        async with TaskGroup() as tg:
            for file in await self.files_from_token(token):
                tg.create_task(
                    self.download_file(
                        token=token,
                        file_id=file,
                        out_dir=out_dir
                    )
                )

    async def download_file(
        self,
        token: str,
        file_id: int,
        out_dir: Path
    ):
        """
        Downloads a single file
        """
        download_endpoint = urlunparse(urlparse(self.base_url)._replace(path="/download.php"))
        async with self.http_client.stream("GET", download_endpoint, params={
            "files_ids": file_id,
            "token": token
        }) as res:
            for content_param in res.headers["Content-Disposition"].split(";"):
                if "filename" in content_param:
                    filename = content_param.split("=")[1].lstrip('"').rstrip('"')
                    break
            else:
                raise Exception("No filename found")

            async with aiofiles.open(out_dir / filename, "wb") as fp:
                async for chunk in res.aiter_raw(chunk_size=8192):
                    await fp.write(chunk)

    async def get_server_info(
        self
    ) -> response.ServerInfo:
        return (await self.http_client.get(f"{self.base_url}/info")).json()

    async def upload_workflow(
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
        transfer = await self.create_transfer({
            "files": [{
                "name": file.name,
                "size": file.stat().st_size
            } for file in files],
            "options": {
                "email_download_complete": True,
            },
            **transfer_args
        })
        self.http_client.params = self.http_client.params.set("roundtriptoken", transfer["roundtriptoken"])
        # Upload each file in parallel
        async with TaskGroup() as tg:
            for file in transfer["files"]:
                tg.create_task(self.upload_complete(
                    file_info=file,
                    path=files_by_name[file["name"]]
                ))

        transfer = await self.update_transfer(
            transfer_id=transfer["id"],
            body={"complete": True}
        )
        return transfer

    async def upload_complete(self,
        file_info: response.File,
        path: Path
    ):
        """Uploads a file and marks the upload as complete"""
        await self.upload_file(
            file_info=file_info,
            path=path
        )
        await self.update_file(
            file_info=file_info,
            body={"complete": True}
        )
