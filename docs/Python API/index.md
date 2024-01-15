# Python API

## Examples

### Upload

```python
from filesender import UserAuth, FileSenderClient
from asyncio import run

async def main():
    user_client = FileSenderClient(
        base_url="https://filesender.aarnet.edu.au",
        auth=UserAuth(
            api_key="kzh1mk1bik1bavgjrggwd6w8u71vyrg5cagevfkt5zv21njodl6hzaiscrok36dtz",
            username="me@institute.edu.au"
        )
    )
    await user_client.prepare()
    transfer = await user_client.upload_workflow(
        files=["my_data.r1.fastq", "my_data.r2.fastq"],
        transfer_args={
            "recipients": ["them@organisation.edu.au"],
            "from": "me@institute.edu.au"
        }
    )

if __name__ == "__main__":
    run(main())
```

### Download

```python
from filesender import UserAuth, FileSenderClient
from asyncio import run
from pathlib import Path

async def main():
    download_client = FileSenderClient(
        base_url="https://filesender.aarnet.edu.au
    )
    
    await download_client.download_files(
        token="hxvmxx9n-2e5u-br7d-4sf5-ypa3-tq55qw43",
        out_dir=Path("~/Downloads")
    )

if __name__ == "__main__":
    run(main())
```

## ::: filesender.FileSenderClient
    options:
        signature_crossrefs: true
        members:
            # Note: these are sorted in terms of user relevance, with the first methods being more important
            - prepare
            - create_guest
            - upload_workflow
            - download_files
            - get_server_info
            - create_transfer
            - update_transfer
            - update_file
            - upload_file
            - download_file
            - upload_complete

## ::: filesender.UserAuth

## ::: filesender.GuestAuth
