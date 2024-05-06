# Introduction

This repository contains a robust client for interacting with [`filesender`](https://github.com/filesender/filesender) file sharing servers.

Although `filesender` comes with [a Python client](https://github.com/filesender/filesender/blob/development/scripts/client/filesender.py), this project has a number of advantages:

* The CLI includes numerous additional features, including the ability to download files, upload to vouchers, report details about the server and more
* Unlike the built-in `filesender` client, this client is provided as a Python package you can `pip install`, causing its dependencies to be automatically installed
* The Python API can be used in other Python applications without needing to use the CLI
* This client is written using async Python, which aims to improve performance without needing a large number of CPU cores

You can install the latest version of the client using `pip install filesender-client`.
Then, you can view the [Command Line](./cli.md) or [Python API](./Python%20API/index.md) docs to get started.
