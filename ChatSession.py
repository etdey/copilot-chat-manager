"""
GitHub Copilot Chat session object

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

from __future__ import annotations  # for forward references in type hints

import hashlib
import json
import logging
import os
import pathlib
from typing import Iterator

from ChatRequest import Request, ChatRequestParseError, ChatRequestEmptyRequest, ChatRequestCanceled


# Logger; may be overridden by users of this module
Log = logging.getLogger(__file__)
Log_Default_Format = '%(levelname)s %(name)s: %(message)s'


class Chat:

    @staticmethod
    def sorting_attributes() -> list[str]:
        """returns a list of valid attribute names for Chat"""
        return ['id', 'created', 'updated']


    def __init__(self, sessionInput: dict | str | os.PathLike, id: str = '', lastUpdate: float = 0.0, workspaceId: str = '<empty>') -> None:
        """
        Initialize the chat session from a file path, dict, or JSON string.

        When sessionInput is a file path, the id and lastUpdate defaults
        are derived from filesystem metadata, and the file format is
        detected from the extension: 
            .json = snapshot  (original extension's format)
            .jsonl = eventlog (new around 1/2026)
        """

        self.id: str = id
        self.updated: float = lastUpdate
        self.created: float = lastUpdate
        self.requests: list[Request] = []
        self.size: int = 0
        self.format_type: str = 'snapshot'
        self.format_version: int = 3

        # Configure logging only if it hasn't been configured yet
        logging.basicConfig(format=Log_Default_Format, force=False)

        # prepare sessionDict from the based on the input format
        if (isinstance(sessionInput, (os.PathLike, pathlib.Path)) or
           (isinstance(sessionInput, str) and os.path.isfile(sessionInput))
        ):
            sessionDict = self._load_from_file(pathlib.Path(sessionInput), lastUpdate)
        elif isinstance(sessionInput, str):
            sessionDict = json.loads(sessionInput)
        elif isinstance(sessionInput, dict):
            # assumes no mutations and no use after init; make copy if this ever changes
            sessionDict = sessionInput
        else:
            raise ValueError("sessionInput must be a file path, dict, or JSON string")

        # generate a stable hash if id is still not set (non-file-path inputs)
        if self.id == '':
            hasher = hashlib.md5()  # this isn't crypto so cool your jets
            hasher.update(json.dumps(sessionDict, sort_keys=True).encode('utf-8'))
            self.id = hasher.hexdigest()

        # attempt to refine creation and last-update timestamps from session content
        if 'creationDate' in sessionDict:
            try:
                self.created = float(sessionDict['creationDate']) / 1000.  # ms -> s
            except (ValueError, TypeError):
                pass  # leave default value
        if 'lastMessageDate' in sessionDict:
            try:
                self.updated = float(sessionDict['lastMessageDate']) / 1000.  # ms -> s
            except (ValueError, TypeError):
                pass  # leave default value

        for req in sessionDict.get('requests', []):
            try:
                r = Request(req)
                self.requests.append(r)
                self.size += r.size
            except ChatRequestEmptyRequest:
                Log.debug(f"chat request is empty in workspace {workspaceId} chat {self.id}; skipping response parsing")
            except ChatRequestCanceled as e:
                Log.debug(f"skipping canceled request in workspace {workspaceId} chat {self.id}: {e}")
            except ChatRequestParseError as e:
                Log.info(f"skipping unparseable request in workspace {workspaceId} chat {self.id}: {e}")


    def _load_from_file(self, filePath: pathlib.Path, lastUpdate: float) -> dict:
        """read chat session from file and auto-detect format"""

        if not filePath.exists():
            raise FileNotFoundError(f"Chat session file not found: {filePath}")

        # Derive id and lastUpdate from filesystem when not supplied by caller
        if self.id == '':
            self.id = filePath.stem
        if lastUpdate == 0.0:
            ctime = os.path.getctime(filePath)
            self.created = ctime
            self.updated = ctime

        with open(filePath, 'r', encoding='utf-8') as f:
            content = f.read()

        # detect file format based on file extension
        ext = filePath.suffix.lower()
        if ext == '.jsonl':
            return self._parse_eventlog(content)
        elif ext == '.json':
            # original format where entire session is one big JSON object
            return json.loads(content)
        else:
            raise ValueError(f"Unsupported chat session file extension: {ext!r}")


    def _parse_eventlog(self, content: str) -> dict:
        """Parse a JSONL event-log file and return a snapshot compatible session dict"""

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return {'requests': []}

        # validate first event which has session metadata
        first_event = json.loads(lines[0])
        if first_event.get('kind') != 0:
            raise ValueError(
                f"JSONL chat session does not begin with a kind:0 snapshot event; "
                f"got kind={first_event.get('kind')!r}"
            )
        v = first_event.get('v', {})
        version = v.get('version')
        if version not in (3,):  # extend tuple when new versions are confirmed
            raise ValueError(f"Unsupported JSONL chat session version: {version!r}")
        self.format_version = version
        self.format_type = 'eventlog'

        created_time_ms: float = float(v.get('creationDate', 0))
        last_time_ms: float = created_time_ms

        # Seed the requests list from the kind:0 snapshot so that back-reference
        # indices in later events align with the session-wide numbering.
        # Snapshot entries already have complete responses; mark them so that
        # post-processing synthesis is skipped for them.
        requests: list[dict] = []
        for req in v.get('requests', []):
            req['_from_snapshot'] = True
            requests.append(req)

        # replay remaining events, one JSON object per line
        for line in lines[1:]:
            event = json.loads(line)
            kind = event.get('kind')
            k = event.get('k')       # present on both kind:1 and kind:2 patch events
            val = event.get('v')

            if kind == 2 and (k is None or k == ['requests']):
                # Append mode: all new request objects added to the session;
                # malformed ones are appended as placeholders and removed in
                # post-processing so that back-reference patches in later
                # events remain correctly indexed.
                for req in (val or []):
                    if 'requestId' not in req or 'message' not in req:
                        Log.warning("inserting placeholder for malformed request in kind:2 event")
                        requests.append({'_placeholder': True})
                    else:
                        requests.append(req)
                        ts = float(req.get('timestamp', 0.0))  # request's timestamp in ms
                        if last_time_ms < ts:  # update if more recent
                            last_time_ms = ts

            elif (kind in (1, 2)
                  and isinstance(k, list) and len(k) == 3
                  and k[0] == 'requests' and isinstance(k[1], int)
                  and 0 <= k[1] < len(requests)):
                # Patch mode; both kind:1 and kind:2 carry targeted patches to
                # previously added request objects back-referenced by index.
                #   k = ["requests", <index>, "<field>"], v = new field value
                req = requests[k[1]]
                if not req.get('_placeholder'):
                    req[k[2]] = val

            elif kind == 1:
                pass  # top-level UI state patch (inputState, selections, etc.) — ignore

            elif kind is not None:
                Log.warning(f"Unrecognized event kind {kind!r} in JSONL session; skipping")

        # count only non-snapshot, non-placeholder entries for the "no requests" warning
        new_requests = [r for r in requests if not r.get('_from_snapshot') and not r.get('_placeholder')]
        if len(lines) > 1 and len(new_requests) == 0:
            Log.debug(f"JSONL session has {len(lines)} events but no kind:2 request events")

        # Post-processing:
        # Synthesize response from result.metadata.toolCallRounds (fallback).
        # For new requests the rich response arrives via a kind:2 patch to req["response"],
        # but VS Code may later overwrite that patch with a cleanup version containing only
        # skipped kinds (e.g. toolInvocationSerialized).  The full plain-text rendering is
        # always preserved in result.metadata.toolCallRounds[*].response, so use that as
        # the authoritative fallback whenever the response list has no usable value entries.
        for req in requests:
            if req.get('_placeholder') or req.get('_from_snapshot'):
                continue
            
            # only synthesize when the patched response is still empty/startup noise
            has_real_response = any(('value' in r and 'kind' not in r) for r in req.get('response', []))
            if has_real_response:
                continue

            # synthesize plain-text for tool calls -- maintains reader's context in final results
            call_rounds = req.get('result', {}).get('metadata', {}).get('toolCallRounds', [])
            parts = []
            for round_ in call_rounds:
                text = round_.get('response', '')
                tool_calls = round_.get('toolCalls', [])
                tool_name = tool_calls[0].get('name', '') if tool_calls else ''
                if text:
                    parts.append(text)
                if tool_name:
                    parts.append(f"\n> *[ran tool: {tool_name}]*\n\n")
            response_text = ''.join(parts)
            if response_text:
                if 'response' not in req:
                    req['response'] = []  # add element if missing
                req['response'].append({'value': response_text})

        # remove placeholder entries from final list of requests
        requests = [req for req in requests if not req.get('_placeholder')]

        return {
            'creationDate': created_time_ms,
            'lastMessageDate': last_time_ms,
            'requests': requests,
        }


    def __len__(self) -> int:
        return len(self.requests)


    def __iter__(self) -> Iterator[tuple[str, str, int]]:
        for r in self.requests:
            yield (r.request, r.response, r.size)
