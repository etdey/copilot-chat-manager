"""
GitHub Copilot Chat session object

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

from __future__ import annotations  # for forward references in type hints

import hashlib, json, logging
from typing import Iterator
from pprint import pformat

from ChatRequest import Request, ChatRequestParseError, ChatRequestEmptyRequest, ChatRequestCanceled


# Logger; may be overridden by users of this module
Log = logging.getLogger(__file__)
Log_Default_Format = '%(levelname)s %(name)s: %(message)s'


class Chat:
    
    @staticmethod
    def sorting_attributes() -> list[str]:
        """returns a list of valid attribute names for Chat"""
        return ['id', 'createDate', 'lastUpdate']


    def __init__(self, sessionInput: dict | str, id: str = '', lastUpdate: float = 0.0, workspaceId: str = '<empty>') -> None:
        """initialize the chat session from a dictionary or JSON string"""
        
        self.id: str = id   # None value is handled later
        self.lastUpdate: float = lastUpdate
        self.createDate: float = lastUpdate  # always same as lastUpdate
        self.requests: list[Request] = []
        self.size: int = 0  # total size of all requests + responses

        # Configure logging only if it hasn't been configured yet
        logging.basicConfig(format=Log_Default_Format, force=False)

        # prepare sessionDict from input
        if isinstance(sessionInput, str):
            sessionDict = json.loads(sessionInput)
        elif isinstance(sessionInput, dict):
            sessionDict = sessionInput
        else:
            raise ValueError("sessionInput must be a dict or JSON string")

        # Generate a stable hash if none was provided        
        if self.id == '':
            hasher = hashlib.md5()  # this isn't crypto so cool your jets
            hasher.update(json.dumps(sessionDict, sort_keys=True).encode('utf-8'))
            self.id = hasher.hexdigest()

        for req in sessionDict.get('requests', []):
            try:
                r = Request(req)
                self.requests.append(r)
                self.size += r.size
            except ChatRequestEmptyRequest as e:
                Log.debug(f"chat request is empty in workspace {workspaceId} chat {self.id}; skipping response parsing")
            except ChatRequestCanceled as e:
                Log.debug(f"skipping canceled request in workspace {workspaceId} chat {self.id}: {e}")
            except ChatRequestParseError as e:
                Log.info(f"skipping unparseable request in workspace {workspaceId} chat {self.id}: {e}")

    def __len__(self):
        return len(self.requests)


    def __iter__(self) -> Iterator[tuple[str, str, int]]:
        for r in self.requests:
            yield (r.request, r.response, r.size)
