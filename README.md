# GitHub Copilot Chat Manager Tool

This package is a tool for managing the GitHub Copilot chat sessions from VSCode that are stored on a local file system within a user's home directory. The impetus behind this tool is that VSCode upgrades clear the chat histories for projects even though the data files still exist on disk. I grew tired of the tedious process of finding previous chat sessions and resurrecting them after a VSCode upgrade.

See the project's `LICENSE` file for details about the software license.


## Setup

You must use at least Python 3.7. There may be constructs that require a higher version, but I know that at least 3.7 is required. 

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

NOTE: If you want to do development and testing, substitute the `requirements-dev.txt` file in the above instructions. Thus, `pip install -r requirements-dev.txt` on Windows. 

## Running 

These are the steps to run the tool.
1. Setup the Python virtual environment (1-time task)
1. Active the Python virtual environment
1. Run `chatmgr.py`
    - Windows: `python chatmgr.py {args...}`
    - MacOS/Linux: `./chatmgr.py {args...}`


### Command Help
Windows:
`python chatmgr.py --help`

MacOS/Linux: 
`./chatmgr.py --help`

```
usage: chatmgr.py [-h] [--storage DIR] [-v] [--parse-only] [--no-sanitize] [--sort NAME]
                  [--reverse] [--raw] [--raw-all] [--workspace ID] [--chat ID]
                  [{list,view,sortkeys,help}]

GitHub Copilot chat manager tool.

positional arguments:
  {list,view,sortkeys,help}
                        command to run (default: list)

options:
  -h, --help            show this help message and exit
  --storage DIR         storage directory for workspaces
  -v, --verbose         enable verbose output
  --parse-only          parse input but do not print anything

Input options:
  --no-sanitize         do not sanitize markdown text

Output options:
  --sort NAME, -s NAME  sort attribute
  --reverse, -r         reverse the sort order
  --raw                 show raw JSON input for chat sessions
  --raw-all             show all raw JSON input for chat sessions

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

Show the available sort keys for the workspace listing:  
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

Show the available sort keys for the chat session listing:  
`python chatmgr.py -w 04da77`

View the requests/responses rendered Markdown for a chat session:  
`python chatmgr.py -w 185d7c -c f040af`

View the raw JSON for request/response elements of a chat session:  
`python chatmgr.py -w 185d7c -c f040af --raw`


## Testing and Development

If you are going to do development and testing, you should install the packages from the `requirements-dev.txt` file as shown above with the virtual environment setup.


### Automated Tests

The Python `unittest` framework is used for automated tests. All of the unit tests can be executed with the `run_tests.sh` shell script on MacOS/Linux or with the `run_tests.ps1` PowerShell script on Windows.

**NOTE:** Ensure that you have activated your Python virtual environment before running the scripts.

For VSCode, the `settings.json` file is configured to allow for the running of automated tests directly within the IDE. 


### VSCode Run and Debug

The included `launch.json` file shows the use of a hidden `--argsExpand` command line argument. This argument is a workaround for the lack of support for the `"argsExpand" : "split"` property in VSCode's Python (debugpy) implementation and allows for the prompting of multiple CLI args before running in debug.

When `--argsExpand` appears as the _first_ option (i.e., `sys.argv[1]`), these actions take place before `argparse.ArgumentParser().parse_args()` is called.
1. `sys.argv[0]` is left as-is
1. `--argsExpand` argument is removed
1. Remaining arguments are joined into one string with whitespace
1. `sys.argv[1:]` becomes the output from `shlex.split()` on the combined argument string


### Build and Setuptools

Build for distribution or install on:

  Windows  
  `python -m build`

  MacOS/Linux  
  `python3 -m build`

There are cleanup scripts included to remove the `build` and `setuptools` artifacts.

  Windows  
  `.\clean.ps1`

  MacOS/Linux  
  `./clean.sh`


## VSCode Workspace Storage

VSCode and its extensions use a local storage directory to track a variety of information about your workspaces -- including GitHub Copilot chat session history. This tool only processes the folders that are related to Copilot chat sessions. This is an overview of the directory structure and the files used by the Copilot extension.

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

This information has been reverse engineered from observed behavior and is not an officially published specification. Thus, future changes to VSCode and/or the GitHub Copilot extension could alter the workspace storage structure. 


## Limitations
This is the "Yes, I know about it and intend to fix it," stuff.

- No operating specific build bundles such as with `pyinstaller`; you have to checkout the source and setup a venv to run it.
- Sort keys are very picky about their names and are slightly different from the displayed output columns.
- No interactive shell to work within; e.g., `cmd` library.
- No export to Obsidian vaults.
- No actual testing on Linux 🐧 but it probably works, right?
- Markdown styling is the vanilla default that you get from the `rich` package.
- No markdown or plain text export options.
