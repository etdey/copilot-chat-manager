"""
Obsidian vault tools

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

from __future__ import annotations  # for forward references in type hints

import argparse
import datetime
import logging
import os
from typing import IO, Any


# Logger; may be overridden by users of this module
Log = logging.getLogger(__file__)
Log_Default_Format = '%(levelname)s %(name)s: %(message)s'


def argparse_groups(parser: argparse.ArgumentParser) -> None:
    """Adds and argument groups to an existing argparser"""

    # defaults from environment vars or calculated vals
    def_vault_basedir = os.environ.get('OBSIDIAN_VAULT_BASEDIR', _default_vault_parent_dir())
    def_vault_name = os.environ.get('OBSIDIAN_VAULT_NAME', None)
    def_vault = os.environ.get('OBSIDIAN_VAULT', None)
    def_note_folder = os.environ.get('OBSIDIAN_NOTE_FOLDER', '')

    # vault options
    grp = parser.add_argument_group('Obsidian vault options')
    grp.add_argument('--vault-name', type=str, metavar='NAME', default=def_vault_name, help='name of vault directory (default: %(default)s)')
    grp.add_argument('--vault-basedir', type=str, metavar='DIR', default=def_vault_basedir, help='parent directory for vaults (default: %(default)s)')
    grp.add_argument('--vault', type=str, metavar='DIR', default=def_vault, help='full path to vault; overrides --vault-name and --vault-basedir')
    grp.add_argument('--vault-noverify', action='store_true', default=False, help='bypass vault validation checks; only directory must exist')

    # note options
    grp = parser.add_argument_group('Obsidian note options')
    grp.add_argument('--note-folder', type=str, metavar='RELPATH', default=def_note_folder, help='folder relative to vault root (default: %(default)s)')
    grp.add_argument('--note-title', type=str, metavar='TITLE', default=None, help='title of the note (without ".md" extension)')
    grp.add_argument('--note', type=str, metavar='FILE', default=None, help='relpath within vault to note file; overrides --note-folder and --note-title')
    grp.add_argument('--note-overwrite', action='store_true', default=False, help='allow replacement of existing note (default: %(default)s)')


def argparse_epilog() -> str:
    """Returns the argparse epilog text for Obsidian-related options"""
    epilog = """
        The Obsidian vault can be specified using the --vault option, or by
        combining --vault-name and --vault-basedir. If neither is specified,
        the default vault parent directory is used (typically 'Documents' or
        'My Documents' in the user's home directory), and no vault name is set.

        The note within the vault can be specified using the --note option,
        or by combining --note-folder or --note-title with the vault path. When
        using the --note option, the ".md" extension will be added if it is not
        given.

        These environment variables are recognized: 
        OBSIDIAN_VAULT_BASEDIR - Default parent directory for vaults 
        OBSIDIAN_VAULT - Full path to vault 
        OBSIDIAN_VAULT_NAME - Name of vault (directory name) 
        OBSIDIAN_NOTE_FOLDER - Note's folder within vault (relative to vault root) 
        """
    return epilog


def new_note_frontmatter(created_ts: float = 0.0, updated_ts: float = 0.0, tags: list[str] = []) -> str:
    """Returns a markdown frontmatter string for a new note with the given title and date"""
    if created_ts == 0.0:
        created_ts = datetime.datetime.now().timestamp()
    if updated_ts == 0.0:
        updated_ts = created_ts
    created_str = _timestamp_format(created_ts)
    updated_str = _timestamp_format(updated_ts)

    frontmatter = f"""---
created: {created_str}
created-ts: {created_ts}
updated: {updated_str}
updated-ts: {updated_ts}
document-type: copilot chat
"""
    # add tags
    if len(tags) > 0:
        tags.insert(0, 'tags:')  # 0th element is the 'tags:' line
        tags_str = "\n  - ".join(tags)
        frontmatter += f"{tags_str}\n"

    frontmatter += "---\n\n"
    return frontmatter


def _timestamp_format(ts: float) -> str:
    """returns a formatted timestamp string"""
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _default_vault_parent_dir() -> str | None:
    """Returns the default parent directory for Obsidian vaults, or None if not found"""
    candidates = ['Documents', 'My Documents']  # in priority order
    home = os.path.expanduser('~')  # user's home directory

    for candidate in candidates:
        parentDir = os.path.join(home, candidate)
        if os.path.isdir(parentDir):
            return parentDir
    return None


class ObsidianValidationError(Exception):
    """Raised when there is a validation error with instantiating the Obsidian vault"""
    pass


class Vault():
    """Represents an Obsidian vault located at a given filesystem path"""

    def __init__(self, options: argparse.Namespace) -> None:        
        self.options = options

        # get full path to vault directory
        self.vault_dir = self._vault_full_path(options.vault, options.vault_name, options.vault_basedir)
        if self.vault_dir is None:
            raise ObsidianValidationError("vault directory could not be determined; specify --vault or both --vault-name and --vault-basedir")
        if not os.path.isdir(self.vault_dir):
            raise ObsidianValidationError(f"vault directory does not exist: {self.vault_dir}")
        if not options.vault_noverify:  # verify unless vault_noverify is True
            self._verify_vault(self.vault_dir)

        # get full path to note that will be created
        self.note_file = self._note_full_path(self.vault_dir, options.note, options.note_folder, options.note_title)
        if self.note_file is None:
            raise ObsidianValidationError("note file could not be determined; specify --note or --note-title")
        self.note_dir = os.path.dirname(self.note_file)
        if not os.path.isdir(self.note_dir):
            raise ObsidianValidationError(f"note directory does not exist: {self.note_dir}")

        options.log.debug(f"Obsidian vault initialized: vault_dir={self.vault_dir}, note_file={self.note_file}")


    def _verify_vault(self, vault_dir: str) -> None:
        """Verifies that the directory looks like a valid Obsidian vault"""
        # check for .obsidian directory
        obsidian_dir = os.path.join(vault_dir, '.obsidian')
        if not os.path.isdir(obsidian_dir):
            raise ObsidianValidationError(f"not a valid Obsidian vault; missing .obsidian directory: {vault_dir}")

        # check for workspace.json file in .obsidian
        workspace_json = os.path.join(obsidian_dir, 'workspace.json')
        if not os.path.isfile(workspace_json):
            raise ObsidianValidationError(f"not a valid Obsidian vault; missing workspace.json file: {obsidian_dir}")


    def _vault_full_path(self, vault: str | None = None, vault_name: str | None = None, vault_basedir: str | None = None) -> str | None:
        if vault:
            return vault  # overrides name and basedir options
        if vault_name and vault_basedir:
            return os.path.join(vault_basedir, vault_name)
        return None  # value is None or one of name/basedir is None


    def _note_folder_full_path(self, vault_dir: str, note_folder: str = '') -> str | None:
        if not vault_dir:
            return None
        return os.path.join(vault_dir, note_folder)


    def _note_full_path(self, vault_dir: str, note: str | None, note_folder: str, note_title: str | None) -> str | None:
        if not note and not note_title:
            return None

        if note_title is None:
            note_title = ''

        assert isinstance(note_folder, str), "note_folder must be a string"
        assert isinstance(note_title, str), "note_title must be a string"

        if note:  # note is relpath+filename
            note = os.path.join(vault_dir, note)
        else:  # build note from vault_dir, note_folder, and note_title
            note = os.path.join(vault_dir, note_folder, note_title)

        # add .md extension if not present
        if note[-2:] != '.md':
            note += ".md"
        if len(note) < 4:  # at least one char plus ".md"
            return None
        return note


    def open_note(self, mode: str = 'r', encoding: str | None = 'utf-8', newline: str | None = None) -> IO[Any]:
        """
        Opens a file within the vault and returns a file object. This will not
        allow overwriting an existing file unless the --note-overwrite option
        was specified.

        Args:
            mode: Same as built-in open() parameter (default: 'r')
            encoding: Same as built-in open() parameter (default: 'utf-8').
            newline: Same as built-in open() parameter (default: None).

        Returns:
            A file object opened in the specified mode.

        Raises:
            FileExistsError: If the file exists and overwriting is not allowed.
        """
        assert self.note_file is not None, "note_file cannot be None after initialization"

        writing_mode = False
        if 'w' in mode or 'a' in mode:
            writing_mode = True

        if writing_mode and os.path.isfile(self.note_file) and not self.options.note_overwrite:
            raise FileExistsError(f"note file already exists (use --note-overwrite to allow replacement): {self.note_file}")

        return open(self.note_file, mode=mode, encoding=encoding, newline=newline)
