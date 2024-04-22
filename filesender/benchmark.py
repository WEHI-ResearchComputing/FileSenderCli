"""
Tools for benchmarking the FileSender client
"""
import resource
import asyncio
import time
from contextlib import contextmanager, ExitStack
from random import randbytes
import tempfile
from pathlib import Path
from typing import Any, Generator, Iterable
from dataclasses import dataclass
import multiprocessing as mp

from filesender.api import FileSenderClient
from filesender.auth import UserAuth

@dataclass
class BenchResult:
    time: float
    "Memory in fractional sections"
    memory: int
    "Memory in bytes"

@contextmanager
def make_tempfile(size: int, **kwargs: Any) -> Generator[Path, Any, None]:
    """
    Makes a temporary binary file filled with `size` random bytes, and returns a path to it
    """
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, **kwargs) as file:
        path = Path(file.name)
        file.write(randbytes(size))
        file.close()
        yield Path(file.name)
        path.unlink()
    
@contextmanager
def make_tempfiles(size: int, n: int = 2, **kwargs: Any) -> Generator[list[Path], Any, None]:
    """
    Makes `n` temporary files of size `size` and yields them as a list via context manager
    """
    with ExitStack() as stack:
        files = [stack.enter_context(make_tempfile(size=size, **kwargs)) for _ in range(n)]
        yield files

async def upload_capture_mem(client_args: dict, upload_args: dict) -> BenchResult:
    """
    Performs an upload, and returns the memory usage in doing so
    """
    client = FileSenderClient(**client_args)
    await client.prepare()
    start = time.monotonic()
    await client.upload_workflow(**upload_args)
    end = time.monotonic()
    return BenchResult(
        memory=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        time = end - start
    )

def upload_capture_mem_sync(*args: Any) -> BenchResult:
    return asyncio.run(upload_capture_mem(*args))

def benchmark(paths: list[Path], read_limit: Iterable[int | float], req_limit: Iterable[int | float], base_url: str, username: str, apikey: str, recipient: str) -> list[BenchResult]:
    """
    Run a test upload using a variety of semaphore settings, and return one result for each.
    """
    # We use multiprocessing so that each benchmark runs in a separate Python interpreter with a separate RSS
    # The spawn context ensures that no memory is shared with the controlling process
    with mp.get_context("spawn").Pool(processes=1) as pool:
        args = [] 
        for concurrent_reads, concurrent_requests in zip(read_limit, req_limit):
            args.append(({
                    "base_url": base_url,
                    "auth": UserAuth(api_key=apikey, username=username),
                    "concurrent_reads": concurrent_reads,
                    "concurrent_requests": concurrent_requests
                },
                {
                    "files": paths,
                    "transfer_args": {"recipients": [recipient], "from": username},
                }
            ))
        return pool.starmap(upload_capture_mem_sync, args)
