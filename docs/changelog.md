# Changelog

## Version 1.2.0

### Added
* `concurrent_reads` argument to the `FileSenderClient()` constructor. This parameter controls the maximum number of file chunks that can be processed at a time.
* `concurrent_requests` argument to the `FileSenderClient()` constructor. This controls the maximum number of API requests the client can be waiting for at a time.
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
