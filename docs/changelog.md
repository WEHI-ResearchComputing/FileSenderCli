# Changelog

## Version 1.1.0

### Added

* `--version` flag, to check for the current package version
* `server-info` command, which is a utility for describing the configuration of the server you are using

### Fixed

* `httpx.PoolTimeout` errors, by enforcing a newer `httpcore` library
* `json.decoder.JSONDecodeError` errors, by not assuming that all errors are JSON. This should better reveal the true underlying error
