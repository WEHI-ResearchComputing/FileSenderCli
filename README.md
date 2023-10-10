# FileSender CLI

## Installation

```bash
pip install git+ssh://git@github.com/multimeric/FileSenderCli
```

## Usage

After installation, the `filesender` command will become available.

```console
$ filesender [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--base-url TEXT`: The URL of the FileSender REST API  [required]
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `download`: Downloads all files associated with a...
* `invite`: Invites a user to send files to you
* `upload`: Sends files to an email of choice
* `upload-voucher`: Uploads files to a voucher that you have...

## `filesender download`

Downloads all files associated with a transfer

**Usage**:

```console
$ filesender download [OPTIONS] TOKEN
```

**Arguments**:

* `TOKEN`: The part of the download URL after "token="  [required]

**Options**:

* `--out-dir DIRECTORY`: Path to the directory to store the output files  [default: /Users/milton.m/Programming/FileSenderCli]
* `--threads INTEGER`: Maximum number of threads to use to download the files concurrently  [default: 1]
* `--help`: Show this message and exit.

## `filesender invite`

Invites a user to send files to you

**Usage**:

```console
$ filesender invite [OPTIONS] RECIPIENT
```

**Arguments**:

* `RECIPIENT`: The email address of the person to invite  [required]

**Options**:

* `--username TEXT`: Your username. This is the username of the person doing the inviting, not the person being invited.  [required]
* `--apikey TEXT`: Your API token. This is the token of the person doing the inviting, not the person being invited.  [required]
* `--help`: Show this message and exit.

## `filesender upload`

Sends files to an email of choice

**Usage**:

```console
$ filesender upload [OPTIONS] FILES...
```

**Arguments**:

* `FILES...`: Files to upload  [required]

**Options**:

* `--username TEXT`: Username of the user performing the upload  [required]
* `--apikey TEXT`: API token of the user performing the upload  [required]
* `--recipients TEXT`: One or more email addresses to send the files  [required]
* `--help`: Show this message and exit.

## `filesender upload-voucher`

Uploads files to a voucher that you have been invited to

**Usage**:

```console
$ filesender upload-voucher [OPTIONS] FILES...
```

**Arguments**:

* `FILES...`: Files to upload  [required]

**Options**:

* `--guest-token TEXT`: The guest token. This is the part of the upload URL after 'vid='  [required]
* `--email TEXT`: The email address that was invited to upload files  [required]
* `--help`: Show this message and exit.
