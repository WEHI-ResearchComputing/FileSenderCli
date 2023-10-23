# Running Tests

## Setup

```bash
pip install pytest
```

## Authentication

The tests require an existing FileSender server to run against, as well as user credentials for using that sever.
To run the tests, you will have to provide these arguments via the command-line:
```bash
pytest test \ 
    --base-url https://filesender.institute.edu/rest.php \ 
    --username myself@gmail.com \ 
    --apikey  cc7795937244e66eb6791b99bc7c2e4171f29630c0f6b28a5f79584570205529\ 
    --recipient recipient@gmail.com 
```

## auth_remote_too_late

If you get an error message involving `auth_remote_too_late`, this means that your connection is too slow, and you should retry on a faster connection.
See this issue for more details and to request improvements: https://github.com/WEHI-ResearchComputing/FileSenderCli/issues/8.
