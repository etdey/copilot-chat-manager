"""
GitHub Copilot Chat Request object

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

from __future__ import annotations  # for forward references in type hints

import json, logging
from pprint import pformat

# Logger; may be overridden by users of this module
Log = logging.getLogger(__file__)
Log_Default_Format = '%(levelname)s %(name)s: %(message)s'

MD_BLOCK_QUOTE_BOOKEND = '```'
MD_INLINE_QUOTE_BOOKEND = '`'

SKIPPED_RESPONSE_KINDS = [
    'codeblockUri',
    'confirmation',
    'command',
    'extensions',
    'prepareToolInvocation',
    'progressMessage',
    'progressTaskSerialized',
    'markdownVuln',
    'toolInvocationSerialized',
    'undoStop',
]

class ChatRequestParseError(Exception):
    """Raised when a chat request cannot be parsed due to an unexpected structure"""
    pass

class ChatRequestEmptyRequest(Exception):
    """Raised when a chat request has no request text"""
    pass

class ChatRequestCanceled(Exception):
    """Raised when a chat request was canceled before completing"""
    pass


class Request:
    def __init__(self, requestInput: dict|str) -> None:
        self.request: str = ''
        self.response: str = ''
        self.size: int = 0  # size of the request + response strings
        self.requestDict: dict = {}  # parsed request dictionary
        self.rawRequest: str = ''  # original request JSON
        self.rawResponse: str = ''  # original response JSON

        if isinstance(requestInput, str):
            self.requestDict = json.loads(requestInput)
        elif isinstance(requestInput, dict):
            self.requestDict = requestInput
        else:
            raise ValueError(f"requestInput must be a dict or JSON string")

        if self.requestDict.get('isCanceled', False) is True:
            raise ChatRequestCanceled(f"request was canceled")

        self.request = self.requestDict.get('message', {}).get('text', '')
        self.rawRequest = json.dumps(self.request, indent=2)
        if self.request == '':
            raise ChatRequestEmptyRequest(f"request is empty")

        responses = self.requestDict.get('response', [])
        self.rawResponse = json.dumps(responses, indent=2)
        if len(responses) == 0:
            responses.append('_No response_')

        responseValue = ''
        hiddenPresentation = False  # Copilot's response was hidden; usually indicates direct file edits
        for resp in responses:
            if not isinstance(resp, dict):
                continue

            if resp.get('kind','') == 'toolInvocation' and resp.get('presentation','') == 'hidden':
                hiddenPresentation = True

            # simple text value response w/o a kind qualifier
            if 'value' in resp and 'kind' not in resp:
                v = resp['value']
                # skip standalone block quote start/stop if the presentation is hidden
                if not hiddenPresentation and v.strip() != MD_BLOCK_QUOTE_BOOKEND:
                    # responseValue += v + '\n\n'
                    responseValue += v

            # edited file in the workspace; make note of the lines that were changed;
            # a future enhancement would be to show the added text; this could be tricky
            # when Copilot uses multiple passes to arrive at a final text
            elif resp.get('kind','') == 'textEditGroup' and resp.get('uri', ''):
                fsPath = resp['uri'].get('fsPath', '**unknown file**')
                responseValue += f"Edited file: `{fsPath}`\n"
                plural = lambda n,s='s': s if n > 1 else ''
                for edit in resp.get('edits', []):
                    for editRegion in edit:
                        if not isinstance(editRegion, dict):
                            raise ChatRequestParseError(f"expected editRegion to be a dict; type is: {type(editRegion)} \n{pformat(editRegion)}")
                        try:
                            text_len = len(editRegion['text'])
                            if text_len == 0:
                                responseValue += f"  - deleted "
                            else:
                                responseValue += f"  - added {text_len} char{plural(text_len)} of text, "
                            
                            line_start = editRegion['range']['startLineNumber']
                            line_end = editRegion['range']['endLineNumber']
                            
                            responseValue += f"line {line_start} "
                            responseValue += f"to {line_end}\n" if line_end > line_start else '\n'
                        except (KeyError, TypeError) as e:
                            raise ChatRequestParseError(f"unknown editRegion dict structure: {e} \n{pformat(editRegion)}")
                responseValue += '\n'  # extra newline after file edit summary
            
            # inline references to files or method names; inline quote it
            elif resp.get('kind','') == 'inlineReference':
                ref = '**unknown reference**'
                ref = resp['inlineReference']['fsPath'] if 'fsPath' in resp['inlineReference'] else ref
                ref = resp['inlineReference']['name'] if 'name' in resp['inlineReference'] else ref

                responseValue += f"{MD_INLINE_QUOTE_BOOKEND}{ref}{MD_INLINE_QUOTE_BOOKEND}"
                if ref == '**unknown reference**':
                    responseValue += f"\n{MD_BLOCK_QUOTE_BOOKEND}{pformat(resp['inlineReference'])}{MD_BLOCK_QUOTE_BOOKEND}\n"
            
            # skip response kinds that aren't useful for reporting
            elif resp.get('kind','') in SKIPPED_RESPONSE_KINDS:
                pass

            # report response kinds that haven't been explicitly handled;
            # these may warrant investigation for possible handling
            elif 'kind' in resp:
                Log.info(f"skipping unhandled response kind: {resp['kind']}")

            # skip responseDict without a 'kind' key
            else:
                pass

        self.response = responseValue

        self.size = len(self.request) + len(self.response)
