from .base import ZoteroAPI, ZoteroError

class ZoteroWeb(ZoteroAPI):
    def __init__(self,library_type,library_id,key=None,**kwargs):
        super().__init__('https://api.zotero.org',library_type,library_id,key,**kwargs)

    async def identify(self):
        data = (await self.request('GET', '/keys/current', absolute=True)).json()
        if not str(data.get('userID', '')).isdigit():
            raise ZoteroError(502, 'Zotero did not return a personal user ID')
        # Explicit allowlist: the official response also contains the secret key.
        return {'user_id': str(data['userID']), 'username': data.get('username', ''),
                'permissions': data.get('access', {})}
