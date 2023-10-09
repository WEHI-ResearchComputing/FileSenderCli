# FileSender CLI

## Installation

`pip install git+https://github.com/multimeric/FileSenderCli.git`

## Usage

After installation, the `filesender` command will become available.
Use `filesender --help` for usage information:

```
                                                                                                                                                                                 
 Usage: filesender [OPTIONS] COMMAND [ARGS]...                                                                                                                                   
                                                                                                                                                                                 
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --base-url                  TEXT                             The URL of the FileSender REST API [default: https://filesender.aarnet.edu.au/rest.php] [required]            │
│    --install-completion        [bash|zsh|fish|powershell|pwsh]  Install completion for the specified shell. [default: None]                                                   │
│    --show-completion           [bash|zsh|fish|powershell|pwsh]  Show completion for the specified shell, to copy it or customize the installation. [default: None]            │
│    --help                                                       Show this message and exit.                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ download                              Downloads all files from a transfer                                                                                                     │
│ invite                                Invites a user to send files to you                                                                                                     │
│ upload                                Sends files to an email of choice                                                                                                       │
│ upload-voucher                        Uploads files to a voucher that you have been invited to                                                                                │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
