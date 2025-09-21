# GitHub Copilot Chat Manager Tool

**EARLY PREVIEW --THIS CODE IS STILL A WORK IN PROGRESS**

This package is a tool for managing the GitHub Copilot chat sessions from VSCode that are stored on a local file system within a user's home directory. The impetus behind this tool is that VSCode upgrades clear the chat histories for projects even though the data files still exist on disk.

See the project's `LICENSE` file for details about the software license.

VSCode's stores more than just GitHub Copilot information within its workspace storage. This tool only shows the folders that are related to a Copilot chat session. This is an overview of the directory structure.

```
workspaceStorage/
    db7749ed1d1c7e177240f4b88daaf7cc/
    d533a5404c1fb33131bf4ff18cf55e1a/
    9d3d359e87669fb4b088d63e3f60f8c6/
        workspace.json
        chatSessions/
            c7b4ae93-9cbe-49ea-93fa-340a95ade508.json
            657ed481-a4b7-4594-bd82-725111948fb1.json
            9903c0b5-4117-4e74-b50f-d3e9b64a87b4.json
            ...
    ...
```

Looked at another way:
```
Collection of all Workspaces
|---Project folder workspace (VSCode: File->Open Folder)
|   |---Chat session details (the conversation)
|   |
|
```


## Setup

You must use at least Python 3.7. There may be constructs that require a higher version, but I know that 3.7 is required. 

1. Clone this repo
1. Create a Python virtual environment
1. Active the virtual environment
1. Install the required packages

NOTE: Each time you run the tool, you will need to activate the Python virtual environment.

### Virtual Environment Creation and Setup

Windows:
```powershell
python -m venv .venv-windows
.venv-windows\Scripts\activate
pip install -r requirements.txt
```

MacOS (or Linux):
```bash
python3 -m venv .venv-macos   # or '.venv-linux'
source .venv-macos/bin/activate
pip3 install -r requirements.txt
```

## Running 

### Help Command
Windows:
`python chatmgr.py --help`

MacOS/Linux: 
`./chatmgr.py --help`

```
usage: chatmgr.py [-h] [--storage DIR] [-v] [--no-sanitize] [--input-encoding ENC] [--sort NAME]
                  [--reverse] [--workspace ID] [--chat ID]
                  [{list,view,sortkeys,help}]

GitHub Copilot chat manager tool.

positional arguments:
  {list,view,sortkeys,help}
                        command to run (default: list)

options:
  -h, --help            show this help message and exit
  --storage DIR         storage directory for workspaces
  -v, --verbose         enable verbose output

Input options:
  --no-sanitize         do not sanitize markdown text
  --input-encoding ENC  input text encoding format (default: utf-8)

Output options:
  --sort NAME, -s NAME  sort attribute
  --reverse, -r         reverse the sort order

Filtering:
  --workspace ID, -w ID
                        select workspace
  --chat ID, -c ID      select chat session

If no workspace is specified, the default is:
C:\Users\{username}\AppData\Roaming\Code\User\workspaceStorage
```

The workspace default directory will change based on your operating system.

### Commands

List all workspaces:  
`python chatmgr.py`

Show the available sort keys:  
`python chatmgr.py sortkeys`

Sorting the workspaces listing by project folder:  
`python chatmgr.py --sort folder`

Reverse sorting by last update time:  
`python chatmgr.py --sort lastUpdate -r`

Listing the chat sessions in a workspace:  
`python chatmgr.py -w 1f0994`  
... elipsis works too:  
`python chatmgr.py -w dbc961...`  
... as does the full id:  
`python chatmgr.py -w f58eb7ffed5d4db975e9f8948c719ca3`

View the requests/responses rendered Markdown for a chat session:  
`python chatmgr.py -w 185d7c -c f040af`


## Limitations
This is the "Yes, I know about it and intend to fix it," stuff.

- Non-text responses, like references to code lines or files in the chat responses are skipped.
- The only output is rendered Markdown on the console; no export or raw Markdown output options.
- Sort keys are very picky about their names and are slightly different from the displayed output columns.
- Markdown styling is the vanilla default that you get from the `rich` package.
- No operating specific build bundles such as with `pyinstaller`; you have to checkout the source and setup a venv to run it.
- No direct testing on non-Windows system; but it _probably_ works, right?
- No unit tests. Sad. 😭
- No interactive shell to work within; e.g., `cmd` library.
- No export to Obsidian vaults.
