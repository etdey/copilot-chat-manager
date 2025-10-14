#! /usr/bin/env python3
"""
GitHub Copilot chat manager tool.

Copyright (c) 2025 by Eric Dey. All rights reserved.

Created: September 2025

"""

import argparse
import datetime
import json
import logging
import os
import shlex
import sys
import urllib.parse

from rich.console import Console
from rich.markdown import Markdown

import Workspace


# Defaults values for arg parsing
Defaults = {
    'userHomeDir': os.path.expanduser('~'),
    'workspaceDirRelWindows': os.path.join('AppData', 'Roaming', 'Code', 'User', 'workspaceStorage'),
    'workspaceDirRelMac': os.path.join('Library', 'Application Support', 'Code', 'User', 'workspaceStorage'),
    'workspaceDirRelLinux': os.path.join('.config', 'Code', 'User', 'workspaceStorage'),
    'sanitizeMarkdown': True,
}


def sanitize_md_text(text: str) -> str:
    # Replace non-standard apostrophes and quotes with ASCII equivalents
    replacements = {
        '\u2019': "'",   # right single quotation mark
        '\u2018': "'",   # left single quotation mark
        '\u201c': '"',   # left double quotation mark
        '\u201d': '"',   # right double quotation mark
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text


def markdown_to_text(markdown: str, printText: bool = True, sanitize: bool = False) -> None:
    if sanitize:
        markdown = sanitize_md_text(markdown)
    md = Markdown(markdown)
    if printText:
        Console().print(md)


def elipsis_id(id: str, begin: int = 6, end: int = 0) -> str:
    """returns an elipsized version of a workspace id"""
    if len(id) < begin + end + 4:
        return id
    return id[:begin] + '...' + id[-end:] if end else id[:begin] + '...'


def folder_url_format(folder: str) -> str:
    """returns a folder path formatted for URL use"""
    name = urllib.parse.unquote(folder)
    return name.replace('file:///', '')


def timestamp_format(ts: float) -> str:
    """returns a formatted timestamp string"""
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def load_workspaces(storageDir: str, sortBy: str = '') -> Workspace.Workspaces:
    """loads the workspaces from the given storage directory"""
    return Workspace.Workspaces(storageDir, sortBy=sortBy)


def print_workspace_summary(workspaces: Workspace.Workspaces) -> None:
    """prints a summary of the workspaces and their chat sessions"""
    md = '# Available Workspaces\n'
    md += f'**Workspace storage:** {folder_url_format(workspaces.storageDir)}  \n'
    md += f'**Workspaces with chat sessions:** {len(workspaces)}\n\n'
    md += '| ID | Workspace Folder | Created | Last Updated | Chats |\n'
    md += '|----|------------------|---------|--------------|-------|\n'
    for w in workspaces:
        md += f'| {elipsis_id(w.id)} | {folder_url_format(w.folder)} | {timestamp_format(w.createDate)} | {timestamp_format(w.lastUpdate)} | {len(w.chats)} |\n'
    markdown_to_text(md, printText=True)


def print_sortkeys(workspace: bool = True, chat: bool = True) -> None:
    """prints the available sort keys for workspaces and chats"""
    if workspace:
        print('Workspace sort keys:', end=' ')
        print(', '.join(Workspace.Workspace.sorting_attributes()))
    if chat:
        print('Chat sort keys:', end=' ')
        print(', '.join(Workspace.Chat.sorting_attributes()))


def mode_global(options: argparse.Namespace) -> None:
    """handle global mode (no workspace or chat specified)"""

    if options.cmd == 'sortkeys':
        print_sortkeys(workspace=True, chat=False)
        return

    if options.cmd == 'list' or options.cmd == 'view':
        workspaces = load_workspaces(options.workspaceStorageDir, sortBy=options.sort)
        print_workspace_summary(workspaces) if options.printmd else None
        return

    options.log.error(f'invalid command: {options.cmd}')
    return


def mode_workspace(options: argparse.Namespace) -> None:
    """handle workspace mode (workspace specified, no chat specified)"""

    if options.cmd == 'sortkeys':
        print_sortkeys(workspace=False, chat=True)
        return

    workspaces = load_workspaces(options.workspaceStorageDir)
    selected_workspace = workspaces.find(options.workspace)
    if selected_workspace is None:
        options.log.error(f'workspace not found: {options.workspace}')
        sys.exit(1)

    printMarkdown = options.printmd

    # sorting for chat sessions
    selected_workspace.sort(sortBy=options.sort)

    md = '# Workspace Details\n'
    md += f'**Workspace ID:** {selected_workspace.id}  \n'
    md += f'**Workspace Folder:** {folder_url_format(selected_workspace.folder or "")}  \n'
    md += f'**Created:** {timestamp_format(selected_workspace.createDate)}  \n'
    md += f'**Last Updated:** {timestamp_format(selected_workspace.lastUpdate)}  \n'
    md += f'**Chat Sessions:** {len(selected_workspace.chats)}\n\n'
    md += '| Chat ID | Created | Requests | Size |\n'
    md += '|---------|---------|----------|------|\n'
    for chat in selected_workspace.chats:
        md += f'| {elipsis_id(chat.id or "")} | {timestamp_format(chat.createDate)} | {len(chat)} | {chat.size} |\n'
    markdown_to_text(md, printText=printMarkdown)


def mode_chat(options: argparse.Namespace) -> None:
    """handle chat mode (workspace and chat specified)"""
    workspaces = load_workspaces(options.workspaceStorageDir)
    selected_workspace = workspaces.find(options.workspace)
    if selected_workspace is None:
        options.log.error(f'workspace not found: {options.workspace}')
        return

    selected_chat = selected_workspace.find(options.chat)
    if selected_chat is None:
        options.log.error(f'chat session not found in workspace {options.workspace}: {options.chat}')
        return

    printMarkdown = options.printmd
    sanitizeText = options.sanitize

    md = '# Chat Session Details\n'
    md += f'**Workspace ID:** {selected_workspace.id}  \n'
    md += f'**Chat ID:** {selected_chat.id}  \n'
    md += f'**Created:** {timestamp_format(selected_chat.createDate)}  \n'
    md += f'**Size (chars):** {selected_chat.size}  \n'
    md += f'**Requests:** {len(selected_chat)}\n\n'
    markdown_to_text(md, printText=printMarkdown)

    if options.raw:
        for i, r in enumerate(selected_chat.requests):
            title = f"## Request {i+1} (raw JSON input):\n"
            quotedJson = '```\n' + r.rawRequest + '\n```\n'
            markdown_to_text(title + quotedJson, printText=printMarkdown, sanitize=sanitizeText)
            title = f"## Copilot Response {i+1} (raw JSON input):\n"
            quotedJson = '```\n' + r.rawResponse + '\n```\n'
            markdown_to_text(title + quotedJson, printText=printMarkdown, sanitize=sanitizeText)
            markdown_to_text('---\n', printText=printMarkdown)
        return

    if options.raw_all:
        for i, r in enumerate(selected_chat.requests):
            title = f"## Request & Response {i+1} (raw JSON input):\n"
            quotedJson = '```\n' + json.dumps(r.requestDict, indent=2) + '\n```\n'
            markdown_to_text(title + quotedJson, printText=printMarkdown, sanitize=sanitizeText)
            markdown_to_text('---\n', printText=printMarkdown)
        return

    for i, (req, resp, _) in enumerate(selected_chat):
        title = f"## Request {i+1}\n"
        markdown_to_text(title + req, printText=printMarkdown, sanitize=sanitizeText)
        title = f"## Copilot Response {i+1}:\n"
        markdown_to_text(title + resp, printText=printMarkdown, sanitize=sanitizeText)
        markdown_to_text('---\n', printText=printMarkdown)


def main(argv: list[str]) -> int:
    me = os.path.basename(argv[0])

    # OS specific default workspace path
    def_workspace = None
    if sys.platform == 'win32':
        def_workspace = os.path.join(Defaults['userHomeDir'], Defaults['workspaceDirRelWindows'])
    elif sys.platform == 'darwin':
        def_workspace = os.path.join(Defaults['userHomeDir'], Defaults['workspaceDirRelMac'])
    elif sys.platform == 'linux':
        def_workspace = os.path.join(Defaults['userHomeDir'], Defaults['workspaceDirRelLinux'])

    description = 'GitHub Copilot chat manager tool.'
    epilog = f'If no workspace is specified, the default is:\n{def_workspace or "No default for this OS"}'
    parser = argparse.ArgumentParser(description=description, epilog=epilog)

    cli_commands = [
        'list',
        'view',
        'sortkeys',
        'help',
    ]

    # Special case handling for VSCode launch.json argsExpand option
    if len(argv) > 1 and argv[1] == '--argsExpand':
        argv.pop(1)  # remove --argsExpand
        if len(argv) > 1:  # still have args to expand
            additionalArgs = ' '.join(argv[1:])
            argv = argv[:1] + shlex.split(additionalArgs)

    # global options
    parser.add_argument('--storage', dest='workspaceStorageDir', metavar='DIR', type=str, help='storage directory for workspaces')
    parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose output')
    parser.add_argument('--parse-only', action='store_true', help='parse input but do not print anything')

    # input options
    grp = parser.add_argument_group('Input options')
    grp.add_argument('--no-sanitize', action='store_true', help='do not sanitize markdown text')

    # output options
    grp = parser.add_argument_group('Output options')
    grp.add_argument('--sort', '-s', type=str, metavar='NAME', default='', help='sort attribute')
    grp.add_argument('--reverse', '-r', action='store_true', help='reverse the sort order')
    grp.add_argument('--raw', action='store_true', help='show raw JSON input for chat sessions')
    grp.add_argument('--raw-all', action='store_true', help='show all raw JSON input for chat sessions')

    # filtering options
    grp = parser.add_argument_group('Filtering')
    grp.add_argument('--workspace', '-w', type=str, metavar='ID', default=None, help='select workspace')
    grp.add_argument('--chat', '-c', type=str, metavar='ID', default=None, help='select chat session')

    # positional arguments
    parser.add_argument('cmd', type=str, nargs='?', choices=cli_commands, default=cli_commands[0], help='command to run (default: %(default)s)')

    options = parser.parse_args(argv[1:])

    # use default workspace directory if none specified
    if not options.workspaceStorageDir:
        options.workspaceStorageDir = def_workspace

    # validate workspace directory
    if not options.workspaceStorageDir:
        print("No workspace specified and no default workspace available for this OS.")
        return 1
    if not os.path.exists(options.workspaceStorageDir):
        print(f"Workspace directory does not exist: {options.workspaceStorageDir}")
        return 1

    # fixup sort specification if reverse specified
    if options.reverse and options.sort != '':
        options.sort = '-' + options.sort

    # sanitize convenience option
    options.sanitize = not options.no_sanitize

    # setup logging
    log_level = logging.DEBUG if options.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s %(name)s: %(message)s', force=True)
    options.log = logging.getLogger(me)

    # setup parse-only mode
    options.printmd = True if not options.parse_only else False
    if options.parse_only and not options.verbose:
        options.log.info("run with --verbose for more parsing details")

    # help command
    if options.cmd == 'help':
        parser.print_help()
        return 0

    mode = 'global'
    if options.workspace is not None:
        mode = 'workspace'
        if options.chat is not None:
            mode = 'chat'

    # error help message
    if options.chat is not None and options.workspace is None:
        print("If --chat is specified, --workspace must also be specified.")
        return 1

    if mode == 'global':
        mode_global(options)
    elif mode == 'workspace':
        mode_workspace(options)
    elif mode == 'chat':
        mode_chat(options)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
