# Changelog

## Version 2.0.0

### Added

* Implement directory tree uploads. You can now pass directory paths anywhere you could previously just pass file paths, including the CLI and the Python API. However, note that currently the directory hierarchy won't be preserved. So if you upload `dir_a/file_a.txt` and `dir_b/file_b.txt`, they will simply be downloaded as `file_a.txt` and `file_b.txt` with their directories stripped out. This is a limitation of the current API. See https://github.com/filesender/filesender/issues/1555 for context.
* A progress bar to uploads

### Fixed

* Memory usage in 1.3.0 was incredibly high, because the entire file was being kept in memory due to a bug. This is now resolved

### Changed

* The `concurrent_reqs` and `concurrent_reads` client arguments, as well as their corresponding CLI arguments have been replaced by `concurrent_chunks` and `concurrent_files`. Read the docs to understand how these work 
* Automatic retries for transient failures.

## Version 1.3.0

### Changed

* Support Python versions back until 3.8 [[#22]](https://github.com/WEHI-ResearchComputing/FileSenderCli/pull/22)

## Version 1.2.1

### Changed

* Removed the annoying `rich` error logs which often made it impossible to determine the true underlying error

### Fixed

* A bug where the FileSender server would respond with a redirect, which would cause the client to fail

## Version 1.2.0

### Added
* [`concurrent_reads`](Python API/index.md#filesender.FileSenderClient) argument to the `FileSenderClient()` constructor. This parameter controls the maximum number of file chunks that can be processed at a time.
* [`concurrent_requests`](Python API/index.md#filesender.FileSenderClient) argument to the `FileSenderClient()` constructor. This controls the maximum number of API requests the client can be waiting for at a time.
* [`benchmark` notebook](https://wehi-researchcomputing.github.io/FileSenderCli/benchmark/) that evaluates how manipulating the above two parameters affect runtime and memory usage
* A simple test that validates the effectiveness of the above parameters
* A `filesender.benchmark` module which contains utilities for benchmarking that are used by both the notebook and the test

## Version 1.1.0

### Added

* `--version` flag, to check for the current package version
* `server-info` command, which is a utility for describing the configuration of the server you are using

### Fixed

* `httpx.PoolTimeout` errors, by enforcing a newer `httpcore` library
* `json.decoder.JSONDecodeError` errors, by not assuming that all errors are JSON. This should better reveal the true underlying error
