# Changelog

## Version 2.1.1

### Changed

* Providing a base URL that ends in `/rest.php` is now deprecated, but is still supported [[#33]](https://github.com/WEHI-ResearchComputing/FileSenderCli/pull/29).

### Fixed

* Base URL was not being set correctly for download operations [[#29]](https://github.com/WEHI-ResearchComputing/FileSenderCli/pull/29).
* Drop support for Python 3.8 as it is now end-of-life, and add support for Python 3.13 [[#31]](https://github.com/WEHI-ResearchComputing/FileSenderCli/pull/31)

## Version 2.1.0

### Added

* A progress bar for file downloads

### Changed

* Files are now downloaded into the appropriate subdirectory. For example if you upload `parent/child.txt`, and then later download that file, the `parent` subdirectory will be created.
* `FileSenderClient.download_file` now has some additional args: `file_size` and `file_name` which will enable better functionality if provided. They are typically obtained from `FileSenderClient._files_from_token`
* All terminal output is now through the `logging` module. You can use the new `--log-level` CLI parameter to configure the amount of info that is printed out.
* Update the CLI default concurrency to 2 for chunks and 1 for files. This seems to be moderately performant without ever failing

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
