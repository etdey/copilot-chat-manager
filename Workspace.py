"""
GitHub CopilotWorkspaces object

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

from __future__ import annotations  # for forward references in type hints

import json, logging, os
from typing import Iterator

from ChatSession import Chat


# Logger; may be overridden by users of this module
Log = logging.getLogger(__file__)
Log_Default_Format = '%(levelname)s %(name)s: %(message)s'


class WorkspaceNoChatSessions(Exception):
    """Raised when a workspace does not contain any chat sessions"""
    pass


class Workspaces:

    def __init__(self, workspaceStorageDir: str, sortBy: str = '') -> None:  
        # Configure logging only if it hasn't been configured yet
        logging.basicConfig(format=Log_Default_Format, force=False)

        self.storageDir = workspaceStorageDir  # directory existence checked in refresh()
        self._sortAttribute = sortBy  # workspaces sorting attribute name
        self._sortReverse = False  # sort descending if attribute name starts with '-'
        self.workspaces = []  # list of Workspace objects
        self.refresh()  # read the workspaces from the filesystem


    def refresh(self, sortBy: str = '') -> None:
        """updates the workspaces information from the filesystem"""
        self.workspaces = []

        if not os.path.exists(self.storageDir):
            Log.error(f"basePath does not exist: {self.storageDir}")
            return

        workspaceDirs = [d for d in os.listdir(self.storageDir) if os.path.isdir(os.path.join(self.storageDir, d))]
        for d in workspaceDirs:
            try:
                w = Workspace(os.path.join(self.storageDir, d))
                self.workspaces.append(w)
            except WorkspaceNoChatSessions as e:
                Log.debug(e)
            except ValueError as e:
                Log.warning(f'skipping invalid workspace directory "{d}": {e}')

        self.sort(sortBy)  # sort the workspaces list


    def sort(self, sortBy: str = ''):
        """Sorts the workspaces list by the given attribute name."""
        if sortBy != '':
            self._sortAttribute = sortBy  # update sorting attribute
        
        if self._sortAttribute == '':
            return
        
        # pull out the reverse flag if specified
        if self._sortAttribute.startswith('-'):
            self._sortReverse = True
            self._sortAttribute = self._sortAttribute[1:]
        
        # **TODO**: implement fuzzy matching of attribute names w/difflib
        if self._sortAttribute not in Workspace.sorting_attributes():
            Log.warning(f'Invalid sort attribute for Workspace: {self._sortAttribute}')
            return
            
        self.workspaces.sort(key=lambda w: getattr(w, self._sortAttribute), reverse=self._sortReverse)


    def find(self, id: str) -> Workspace | None:
        """finds a workspace by its ID; supports truncated IDs ending with ..."""
        workspace_id = id.strip().lower().rstrip('.')
        for w in self.workspaces:
            if w.id.startswith(workspace_id):
                return w
        return None


    def __len__(self):
        return len(self.workspaces)
    

    def __iter__(self) -> Iterator[Workspace]:
        for w in self.workspaces:
            yield w


class Workspace:
    
    @staticmethod
    def sorting_attributes() -> list[str]:
        """returns a list of valid sorting attribute names for Workspace"""
        return ['id', 'createDate', 'lastUpdate', 'folder']
    

    def __init__(self, storageDir: str, sortBy: str = '') -> None:
        # Configure logging only if it hasn't been configured yet
        logging.basicConfig(format=Log_Default_Format, force=False)

        self.storageDir = storageDir
        if not os.path.exists(self.storageDir):
            raise ValueError(f"workspace folder does not exist: {self.storageDir}")

        self.chatSessionsFolder = os.path.join(self.storageDir, "chatSessions")
        if not os.path.exists(self.chatSessionsFolder):
            raise WorkspaceNoChatSessions(f"workspace does not contain any chat sessions: {self.chatSessionsFolder}")

        self._sortAttribute = sortBy  # chats sorting attribute name
        self._sortReverse = False  # sort descending if attribute name starts with '-'
        self.createDate = os.path.getctime(storageDir)
        self.lastUpdate = self.createDate # default until we find chat sessions
        self.chats: list[Chat] = []  # chat objects
        self.folder = ''  # project directory this workspace is associated with
        self.id = os.path.basename(self.storageDir)  # id is the storageDir name

        self.refresh()  # read the session files for workspace


    def refresh(self, sortBy: str = '') -> None:
        """updates the workspace information from the filesystem"""

        self.metadata = {}
        metadataFile = os.path.join(self.storageDir, "workspace.json")
        if not os.path.exists(metadataFile):
            Log.warning(f"workspace metadata file does not exist: {metadataFile}")
        else:
            with open(metadataFile, "r") as sessionFile:
                self.metadata = json.load(sessionFile)
            self.folder = self.metadata.get('folder', '')

        if not os.path.exists(self.chatSessionsFolder):
            Log.error(f"chatSessionsFolder does not exist: {self.chatSessionsFolder}")
            self.lastUpdate = self.createDate
            return

        self.lastUpdate = self.createDate  # default until we find chat sessions

        # scan directory for chat session files
        sessionFiles = [f for f in os.listdir(self.chatSessionsFolder) if os.path.isfile(os.path.join(self.chatSessionsFolder, f))]
        if not sessionFiles:
            return  # stop since no chat sessions files found
        
        file_dates = [(f, os.path.getctime(os.path.join(self.chatSessionsFolder, f))) for f in sessionFiles]
        self.lastUpdate = max(file_dates, key=lambda x: x[1])[1]

        # load chat sessions
        self.chats = []
        for sessionFile in sessionFiles:
            try:
                with open(os.path.join(self.chatSessionsFolder, sessionFile), 'r', encoding='utf-8') as sf:
                    chat_id = os.path.splitext(sessionFile)[0]
                    chat_lastUpdate = os.path.getctime(os.path.join(self.chatSessionsFolder, sessionFile))
                    chat = Chat(sf.read(), id=chat_id, lastUpdate=chat_lastUpdate, workspaceId=self.id)
                    self.chats.append(chat)
            except Exception as e:
                Log.warning(f"failed to load chat session from file {sessionFile}: {e}")

        self.sort(sortBy)  # sort chats by the specified attribute name


    def sort(self, sortBy: str = ''):
        """Sorts the chats list by the given attribute name."""
        if sortBy != '':
            self._sortAttribute = sortBy  # update sorting attribute
        
        if self._sortAttribute == '':
            return

        # pull out the reverse flag if specified
        if self._sortAttribute.startswith('-'):
            self._sortReverse = True
            self._sortAttribute = self._sortAttribute[1:]

        # **TODO**: implement fuzzy matching of attribute names w/difflib
        if self._sortAttribute not in Chat.sorting_attributes():
            Log.warning(f'Invalid sort attribute for Chat: {self._sortAttribute}')
            return

        self.chats.sort(key=lambda c: getattr(c, self._sortAttribute), reverse=self._sortReverse)


    def find(self, id: str) -> Chat | None:
        """finds a chat session by its ID; supports truncated IDs ending with ..."""
        chat_id = id.strip().lower().rstrip('.')
        for c in self.chats:
            if c.id.startswith(chat_id):
                return c
        return None
