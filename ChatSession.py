"""
GitHub Copilot Chat session object

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

import hashlib, json, logging
from pprint import pformat

# Logger; may be overridden by users of this module
Log = logging.getLogger(__file__)
Log_Default_Format = '%(levelname)s %(name)s: %(message)s'


class Chat:
    
    @staticmethod
    def sorting_attributes() -> list[str]:
        """returns a list of valid attribute names for Chat"""
        return ['id', 'createDate', 'lastUpdate']

    
    def __init__(self, sessionInput: dict | str, id: str|None = None, lastUpdate: float = 0.0) -> None:
        """initialize the chat session from a dictionary or JSON string"""
        
        self.id = id   # None value is handled later
        self.lastUpdate = lastUpdate
        self.createDate = lastUpdate  # always same as lastUpdate
        self.requests = []
        self.responses = []

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
        if self.id is None:
            hasher = hashlib.md5()  # this isn't crypto so cool your jets
            hasher.update(json.dumps(sessionDict, sort_keys=True).encode('utf-8'))
            self.id = hasher.hexdigest()

        for req in sessionDict.get('requests', []):
            self.requests.append(req.get('message', {}).get('text', ''))

            
            responses = req.get('response', [])
            if len(responses) == 0:
                Log.debug("no responses found for a request.")
                # self.responses.append('_No response_')

            responseValue = ''
            for resp in responses:
                if isinstance(resp, dict) and 'value' in resp:
                    responseValue += resp['value'] + '\n\n'
            self.responses.append(responseValue)

        # Ensure requests and responses are of the same length
        if len(self.requests) != len(self.responses):
            raise ValueError(f"requests and responses list sizes are unequal: {len(self.requests)} != {len(self.responses)}")
    

    def __len__(self):
        return len(self.requests)


    def __iter__(self):
        return zip(self.requests, self.responses)
