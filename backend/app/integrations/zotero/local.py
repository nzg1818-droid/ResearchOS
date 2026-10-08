from urllib.parse import urlparse
from .base import ZoteroAPI, ZoteroError

class ZoteroLocal(ZoteroAPI):
    def __init__(self,endpoint,library_type='user',library_id='0',key=None,**kwargs):
        parsed=urlparse(endpoint)
        if parsed.scheme!='http' or parsed.hostname not in ('localhost','127.0.0.1','::1') or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ZoteroError(422,'Local Zotero endpoint must be an unauthenticated loopback HTTP URL')
        super().__init__(endpoint,library_type,library_id,key,**kwargs)
        self.local=True;self.writable=False
    async def authorize(self):
        await self.health()
        if not self.writable:raise ZoteroError(405,'Local Zotero does not support write authorization; use Web API')
        return (await self.request('POST','/local/authorize',absolute=True,json={'appName':'ResearchOS'})).json()
