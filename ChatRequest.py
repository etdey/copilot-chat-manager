"""
GitHub Copilot Chat Request object

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

from __future__ import annotations  # for forward references in type hints

import json, logging

# Logger; may be overridden by users of this module
Log = logging.getLogger(__file__)
Log_Default_Format = '%(levelname)s %(name)s: %(message)s'


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
            raise ValueError("requestInput must be a dict or JSON string")

        self.request = self.requestDict.get('message', {}).get('text', '')
        self.rawRequest = json.dumps(self.request, indent=2)

        responses = self.requestDict.get('response', [])
        self.rawResponse = json.dumps(responses, indent=2)
        if len(responses) == 0:
            Log.debug("no responses found for a request.")
            # self.responses.append('_No response_')

        responseValue = ''
        for resp in responses:
            if isinstance(resp, dict) and 'value' in resp:
                responseValue += resp['value'] + '\n\n'
        self.response = responseValue

        self.size = len(self.request) + len(self.response)
