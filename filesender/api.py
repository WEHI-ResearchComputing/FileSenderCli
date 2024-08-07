import ssl
from typing import Any, Callable, Coroutine, Generator, Iterable, List, Optional, Tuple, AsyncIterator, Set
from bs4 import BeautifulSoup
import filesender.response_types as response
import filesender.request_types as request
from urllib.parse import urlparse, urlunparse, unquote
from filesender.auth import Auth
from pathlib import Path
from httpx import Request, AsyncClient, HTTPStatusError, RequestError, ReadError
from asyncio import Semaphore, gather
import aiofiles
from aiostream import pipe, stream
from contextlib import contextmanager
from tenacity import AsyncRetrying, RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_fixed, retry_if_exception
# from httpcore import ReadError

def should_retry(e: BaseException) -> bool:
    """
    Returns True if the exception is a transient exception from the FileSender server,
    that can be retried.
    """
    if isinstance(e, ReadError):
        # Seems to be just a bug in the backend
        # https://github.com/encode/httpx/discussions/2941 
        return True
    elif isinstance(e, HTTPStatusError) and e.response.status_code == 500 and e.response.json()["message"] == "auth_remote_too_late":
        # These errors are caused by lag between creating the response and it being received
        return True
    return False


def url_without_scheme(url: str) -> str:
    """
    Returns the URL in the appropriate format for the signature calculation, namely:
    • Without a scheme
    • Without URL encoding
    • With query parameters
    """
    return unquote(urlunparse(urlparse(url)._replace(scheme="")).lstrip("/"))


@contextmanager
def raise_status():
    """
    Does nothing if the response was successful.
    If it failed, throws a user friendly error
    """
    try:
        yield
    except HTTPStatusError as e:
        raise Exception(
            f"Request failed with content {e.response.text} for request {e.request.method} {e.request.url}"
        ) from e
    except RequestError as e:
        # TODO: check for SSL read error
        raise Exception(
            f"Request failed for request {e.request.method} {e.request.url}"
        ) from e


async def yield_chunks(path: Path, chunk_size: int) -> AsyncIterator[Tuple[bytes, int]]:
    """
    Yields (chunk, offset) tuples from a file, chunked by chunk_size.
    Each chunk is read in serial, so a single call to this will not be parallelised.
    However, multiple files can be read in parallel by gathering multiple calls to this.
    """
    async with aiofiles.open(path, "rb") as fp:
        offset = 0
        while True:
            chunk = await fp.read(chunk_size)
            if not chunk:
                break
            yield chunk, offset
            offset += len(chunk)

def iter_files(paths: Iterable[Path], root: Optional[Path] = None) -> Iterable[Tuple[str, Path]]:
    """
    Recursively yields (name, path) tuples for all files included in the input path, or that are children of these paths
    """
    for path in paths:
        if path.is_dir():
            # Recurse into directories
            if root is None:
                # If this is a top level directory, then its parent becomes the root
                yield from iter_files(path.iterdir(), root = path.parent)
            else:
                # Preserve the same root when recursing
                yield from iter_files(path.iterdir(), root = root)
        else:
            if root is None:
                # If this is a top level file, just use the filename directly
                yield path.name, path
            else:
                # If this is a nested file, use the relative path from the root directory as the name
                yield str(path.relative_to(root)), path

class FileSenderClient:
    """
    A client that can be used to programmatically interact with FileSender.
    """

    #: The base url of the file sender's API. For example https://filesender.aarnet.edu.au/rest.php
    base_url: str
    #: Size of upload chunks
    chunk_size: Optional[int]
    #: Authentication provider that will be used for all privileged requests
    auth: Auth
    # Session to use for all HTTP requests
    http_client: AsyncClient
    concurrent_files: Optional[int]
    concurrent_chunks: Optional[int]

    def __init__(
        self,
        base_url: str,
        chunk_size: Optional[int] = None,
        auth: Auth = Auth(),
        concurrent_files: Optional[int] = None,
        concurrent_chunks: Optional[int] = None,
    ):
        """
        Args:
            base_url: The base URL for the FileSender instance you want to interact with.
                This should just be a host name such as `https://filesender.aarnet.edu.au`,
                and should *not* include `/rest.php` or any other path element.
            chunk_size: The chunk size (in bytes) used for uploading, which is the amount of data that is sent to the server per request.
                By default this is the maximum chunk size allowed by the server, but you might want to adjust this to reduce memory
                usage or because you are getting timeout errors.
            auth: The authentication method.
                This is optional, but you almost always want to provide it.
                Generally you will want to use [`UserAuth`][filesender.UserAuth] or [`GuestAuth`][filesender.GuestAuth].
            concurrent_reads: The maximum number of file chunks that can be processed at a time. Reducing this number will decrease the memory
                usage of the application. None, the default value, sets no limit.
                See <https://wehi-researchcomputing.github.io/FileSenderCli/benchmark> for a detailed explanation of this parameter.
            concurrent_requests: The maximum number of API requests the client can be waiting for at a time. Reducing this number will decrease the memory
                usage of the application. None, the default value, sets no limit.
                See <https://wehi-researchcomputing.github.io/FileSenderCli/benchmark> for a detailed explanation of this parameter.
        """
        self.base_url = base_url
        self.auth = auth
        # FileSender seems to sometimes use redirects
        self.http_client = AsyncClient(timeout=None, follow_redirects=True)
        self.chunk_size = chunk_size
        self.concurrent_chunks = concurrent_chunks
        self.concurrent_files = concurrent_files



    async def prepare(self) -> None:
        """
        Checks that the chunk size is appropriate and/or sets the chunk size based on the server info.
        This should always be run before using the client.
        """
        info = await self.get_server_info()
        if self.chunk_size is None:
            self.chunk_size = info["upload_chunk_size"]
        elif self.chunk_size > info["upload_chunk_size"]:
            raise Exception(
                f"--chunk-size can't be greater than the server's maximum supported chunk size. For this server, the maximum is {info['upload_chunk_size']}"
            )

    # @retry(retry=retry_if_exception_type(ReadError), wait=wait_fixed(0.1))
    async def _sign_send(self, request: Request) -> Any:
        """
        Signs a request and sends it, returning the JSON result
        """
        async with self._req_sem:
            try:
                with raise_status():
                    async for attempt in AsyncRetrying(retry=retry_if_exception(should_retry), wait=wait_fixed(0.1), stop=stop_after_attempt(5)):
                        with attempt:
                            self.auth.sign(request, self.http_client)
                            res = await self.http_client.send(request)
                            res.raise_for_status()
            except RetryError:
                pass
        return res.json()

    async def create_transfer(
        self,
        body: request.Transfer,
    ) -> response.Transfer:
        """
        Tells FileSender that you intend to start building a new transfer.
        Generally you should use [`upload_workflow`][filesender.FileSenderClient.upload_workflow] instead of this, which is much more user friendly.

        Params:
            body: See [`Transfer`][filesender.request_types.Transfer].

        Returns:
            : See [`Transfer`][filesender.response_types.Transfer] (this is a different type from the input parameter).
        """
        return await self._sign_send(
            self.http_client.build_request(
                "POST",
                f"{self.base_url}/transfer",
                json=body,
            )
        )

    async def update_transfer(
        self,
        transfer_id: int,
        body: request.TransferUpdate,
    ) -> response.Transfer:
        """
        Updates an existing transfer, e.g. to indicate that it has finished.
        Generally you should use [`upload_workflow`][filesender.FileSenderClient.upload_workflow] instead of this, which is much more user friendly.

        Params:
            transfer_id: Identifier obtained from the result of [`create_transfer`][filesender.FileSenderClient.create_transfer]
            body: See [`TransferUpdate`][filesender.request_types.TransferUpdate]

        Returns:
            : See [`Transfer`][filesender.response_types.Transfer]
        """
        return await self._sign_send(
            self.http_client.build_request(
                "PUT",
                f"{self.base_url}/transfer/{transfer_id}",
                json=body,
            )
        )

    async def update_file(
        self,
        file_info: response.File,
        body: request.FileUpdate,
    ) -> None:
        """
        Updates metadata for an existing file, e.g. to indicate that it has finished.
        Generally you should use [`upload_workflow`][filesender.FileSenderClient.upload_workflow] instead of this, which is much more user friendly.

        Params:
            file_info: Identifier obtained from the result of [`create_transfer`][filesender.FileSenderClient.create_transfer]
            body: See [`FileUpdate`][filesender.request_types.FileUpdate]
        """
        await self._sign_send(
            self.http_client.build_request(
                "PUT",
                f"{self.base_url}/file/{file_info['id']}",
                params={"key": file_info["uid"]},
                json=body,
            )
        )

    async def upload_file(self, file_info: response.File, path: Path, progress_hook: ProgressHook = None) -> AsyncIterator[None]:
        """
        Uploads a file, with multiple chunks being uploaded in parallel
        Generally you should use [`upload_workflow`][filesender.FileSenderClient.upload_workflow] instead of this, which is much more user friendly.

        Params:
            file_info: Identifier obtained from the result of [`create_transfer`][filesender.FileSenderClient.create_transfer]
            path: File path to the file to be uploaded
            progress_hook: An optional function with the signature (bytes_sent: int, total_bytes: int) that will be called after each chunk

        Returns: An async generator. You can force the uploads to occur using `list()`.
        """
        if self.chunk_size is None:
            raise Exception(".prepare() has not been called!")

        async def _task_generator(chunk_size: int) -> AsyncIterator[Tuple[response.File, int, bytes]]:
            async for chunk, offset in yield_chunks(path, chunk_size):
                yield file_info, offset, chunk

        # progress = 0
        async with (
            stream.iterate(
                _task_generator(self.chunk_size)
            ) | pipe.starmap(
            self._upload_chunk,
            task_limit=2
        )).stream() as streamer:
            async for _ in streamer:
                pass
                # if progress_hook is not None:
                #     progress += self.chunk_size
                #     progress_hook(progress, file_info["size"])

    async def _upload_chunk(
        self,
        file_info: response.File,
        offset: int,
        chunk: bytes,
    ) -> None:
        """
        Internal function to upload a single chunk of data for a file
        """
        return await self._sign_send(
            self.http_client.build_request(
                "PUT",
                f"{self.base_url}/file/{file_info['id']}/chunk/{offset}",
                params={"key": file_info["uid"]},
                content=chunk,
                headers={
                    "Content-Type": "application/octet-stream",
                    "X-Filesender-File-Size": str(file_info["size"]),
                    "X-Filesender-Chunk-Offset": str(offset),
                    "X-Filesender-Chunk-Size": str(len(chunk)),
                },
            )
        )

    async def create_guest(self, body: request.Guest) -> response.Guest:
        """
        Sends a voucher to a guest to invite them to send files

        Params:
            body: see [`Guest`][filesender.request_types.Guest]

        Returns:
            : See [`Guest`][filesender.response_types.Guest]
        """
        return await self._sign_send(
            self.http_client.build_request("POST", f"{self.base_url}/guest", json=body)
        )

    async def _files_from_token(self, token: str) -> Set[int]:
        """
        Internal function that returns a list of file IDs for a given guest token
        """
        download_page = await self.http_client.get(
            "https://filesender.aarnet.edu.au", params={"s": "download", "token": token}
        )
        files: Set[int] = set()
        for file in BeautifulSoup(download_page.content, "html.parser").find_all(
            class_="file"
        ):
            files.add(int(file.attrs["data-id"]))
        return files

    async def download_files(
        self,
        token: str,
        out_dir: Path
    ) -> None:
        """
        Downloads all files for a transfer.
         
        Note that currently the directory hierarchy won't be preserved. So if the original user uploaded `dir_a/file_a.txt` and `dir_b/file_b.txt`, they will simply be downloaded as `file_a.txt` and `file_b.txt` with their directories stripped out. This is a limitation of the current API. See https://github.com/filesender/filesender/issues/1555 for context.

        Params:
            token: Obtained from the transfer email. The same as [`GuestAuth`][filesender.GuestAuth]'s `guest_token`.
            out_dir: The path to write the downloaded files.
        """
        # Each file is downloaded in parallel
        tasks = [
            self.download_file(token=token, file_id=file, out_dir=out_dir)
            for file in await self._files_from_token(token)
        ]
        await gather(*tasks)

    async def download_file(
        self,
        token: str,
        file_id: int,
        out_dir: Path,
        key: Optional[bytes] = None,
        algorithm: Optional[str] = None,
    ) -> None:
        """
        Downloads a single file.

        Params:
            token: Obtained from the transfer email. The same as [`GuestAuth`][filesender.GuestAuth]'s `guest_token`.
            file_id: A single file ID indicating the file to be downloaded.
            out_dir: The path to write the downloaded file.
        """
        download_endpoint = urlunparse(
            urlparse(self.base_url)._replace(path="/download.php")
        )
        async with self.http_client.stream(
            "GET", download_endpoint, params={"files_ids": file_id, "token": token}
        ) as res:
            for content_param in res.headers["Content-Disposition"].split(";"):
                if "filename" in content_param:
                    filename = content_param.split("=")[1].lstrip('"').rstrip('"')
                    break
            else:
                raise Exception("No filename found")

            async with aiofiles.open(out_dir / filename, "wb") as fp:
                async for chunk in res.aiter_raw(chunk_size=8192):
                    await fp.write(chunk)

    async def get_server_info(self) -> response.ServerInfo:
        """
        Returns all information known about the current FileSender server.

        Returns:
            : See [`ServerInfo`][filesender.response_types.ServerInfo].
        """
        return (await self.http_client.get(f"{self.base_url}/info")).json()

    async def upload_workflow(
        self, files: List[Path], transfer_args: request.PartialTransfer = {}, progress_hook: ProgressHook = None
    ) -> response.Transfer:
        """
        High level function for uploading one or more files

        Args:
            files: A list of files and/or directories to upload.
            transfer_args: Additional options to include when creating the transfer, for example a subject or message. See [`PartialTransfer`][filesender.request_types.PartialTransfer].
            progress_hook: An optional function that takes (current_bytes, total_bytes), which is called periodically, for example to update a progress bar.

        Returns:
            : See [`Transfer`][filesender.response_types.Transfer]
        """
        files_by_name = {key: value for key, value in iter_files(files)}
        file_info: List[request.File] = [{"name": name, "size": file.stat().st_size} for name, file in files_by_name.items()]
        transfer = await self.create_transfer(
            {
                "files": file_info,
                "options": {
                    "email_download_complete": True,
                },
                **transfer_args,
            }
        )
        current_bytes: int = 0
        total_bytes = sum(file["size"] for file in file_info)
        self.http_client.params = self.http_client.params.set(
            "roundtriptoken", transfer["roundtriptoken"]
        )
        # Adapter hook that applies to the entire transfer, not just one file
        def _progress_hook(bytes: int, total: int):
            nonlocal current_bytes
            if progress_hook is not None:
                current_bytes += self.chunk_size
                progress_hook(current_bytes, total_bytes)

        async def _upload_args() -> AsyncIterator[tuple[request.File, Path, ProgressHook]]:
            for file in transfer["files"]:
            # Skip folders, which aren't real
                if file["name"] in files_by_name:
                    yield file, files_by_name[file["name"]], _progress_hook

        # Upload each file in parallel
        await aiostream.stream.starmap(_upload_args(), self.upload_complete, ordered=False, task_limit=self.concurrent_files)

        # Mark the transfer as complete
        transfer = await self.update_transfer(
            transfer_id=transfer["id"], body={"complete": True}
        )
        return transfer

    async def upload_complete(self, file_info: response.File, path: Path, progress_hook: ProgressHook = None) -> None:
        """
        Uploads a file and marks the upload as complete.
        Generally you should use [`upload_workflow`][filesender.FileSenderClient.upload_workflow] instead of this, which is much more user friendly.
        """
        await self.upload_file(file_info=file_info, path=path, progress_hook=progress_hook)
        await self.update_file(file_info=file_info, body={"complete": True})
