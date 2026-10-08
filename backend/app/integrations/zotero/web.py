from .base import ZoteroAPI

class ZoteroWeb(ZoteroAPI):
    def __init__(self,library_type,library_id,key=None,**kwargs):
        super().__init__('https://api.zotero.org',library_type,library_id,key,**kwargs)
