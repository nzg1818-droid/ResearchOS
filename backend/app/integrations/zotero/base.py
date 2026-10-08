"""Official Zotero v3 HTTP operations, including optimistic concurrency."""
import asyncio
import hashlib
from pathlib import Path
from urllib.parse import unquote, urlparse
import uuid
import httpx
from ..capabilities import ProviderStatus

class ZoteroError(Exception):
    def __init__(self, status, message): self.status=status; super().__init__(message)

class ZoteroAPI:
    def __init__(self, endpoint, library_type, library_id, key=None, server_id='', transport=None):
        self.endpoint=endpoint.rstrip('/')
        self.library=f"/{'groups' if library_type=='group' else 'users'}/{library_id}"
        self.key=key;self.server_id=server_id;self.version=0;self.transport=transport
        self.writable=True;self.local=False

    async def request(self, method, suffix='', *, absolute=False, **kwargs):
        if method!='GET' and not self.writable: raise ZoteroError(405,'This Zotero Local API is read-only; use Web API for writes')
        headers={'Zotero-API-Version':'3'}
        if self.key: headers['Zotero-API-Key']=self.key
        if self.server_id: headers['Zotero-Server-ID']=self.server_id
        headers.update(kwargs.pop('headers',{}))
        url=self.endpoint+('' if absolute else self.library)+suffix
        try:
            async with httpx.AsyncClient(transport=self.transport,timeout=45,follow_redirects=False) as client:
                for attempt in range(3):
                    response=await client.request(method,url,headers=headers,**kwargs)
                    if response.status_code not in (429,503) or attempt==2: break
                    try: delay=min(5,max(0,float(response.headers.get('Retry-After','1'))))
                    except ValueError: delay=1
                    await asyncio.sleep(delay)
        except httpx.HTTPError:
            raise ZoteroError(503,'Zotero connection failed; check endpoint/network and try again') from None
        if response.status_code>=400:
            messages={401:'Zotero authorization expired or invalid',403:'Zotero access denied; check API permissions',404:'Zotero item or library not found',412:'Zotero changed since the last read; refresh and resolve conflict',413:'Zotero storage quota or upload limit exceeded',429:'Zotero rate limit; retry later'}
            raise ZoteroError(response.status_code,messages.get(response.status_code,f'Zotero request failed ({response.status_code})'))
        self.version=max(self.version,int(response.headers.get('Last-Modified-Version',0)))
        return response

    async def health(self):
        r=await self.request('GET','/items',params={'limit':1})
        server=r.headers.get('Zotero-Server-ID','')
        if self.local:
            if self.server_id and server and self.server_id!=server: raise ZoteroError(412,'Local Zotero server identity changed; configure a new connection')
            self.server_id=server
            self.writable=bool(server)
        capabilities=['health','import','attachments','open-external']
        if self.writable: capabilities+=['export','sync','upload']
        return ProviderStatus(True,'zotero-local' if self.local else 'zotero-web',capabilities,self.server_id,self.version,'Connected' if self.writable else 'Connected (read-only Local API)')

    async def paginate(self,suffix,params=None):
        found=[];start=0
        while True:
            r=await self.request('GET',suffix,params={**(params or {}),'limit':100,'start':start})
            page=r.json()
            if not isinstance(page,list): raise ZoteroError(502,'Unexpected Zotero list response')
            found.extend(page)
            if len(page)<100: return found
            start+=len(page)

    async def collections(self): return await self.paginate('/collections')
    async def items(self,collection=None,since=None):
        params={'since':since} if since is not None and (not self.local or self.writable) else {}
        return await self.paginate(f'/collections/{self.safe_key(collection)}/items' if collection else '/items',params)
    async def children(self,key): return await self.paginate(f'/items/{self.safe_key(key)}/children')
    async def item(self,key): return (await self.request('GET',f'/items/{self.safe_key(key)}')).json()
    @staticmethod
    def safe_key(key):
        if not isinstance(key,str) or not key.isalnum() or len(key)>32: raise ZoteroError(422,'Invalid Zotero item or collection key')
        return key
    async def create(self,data):
        r=await self.request('POST','/items',json=[data],headers={'Zotero-Write-Token':uuid.uuid4().hex})
        result=r.json()
        if result.get('failed'): raise ZoteroError(422,'Zotero rejected item fields or permissions')
        item=result.get('successful',{}).get('0')
        if item: return item
        key=result.get('success',{}).get('0')
        if key: return await self.item(key)
        raise ZoteroError(502,'Zotero did not return the created item')
    async def update(self,key,version,patch):
        await self.request('PATCH',f'/items/{self.safe_key(key)}',json=patch,headers={'If-Unmodified-Since-Version':str(version)})
        return await self.item(key)
    async def download(self,key):
        r=await self.request('GET',f'/items/{self.safe_key(key)}/file')
        if r.is_redirect:
            url=r.headers.get('Location','');parsed=urlparse(url)
            if parsed.scheme=='file' and self.local:
                path=unquote(parsed.path)
                if len(path)>2 and path[0]=='/' and path[2]==':':path=path[1:]
                return await asyncio.to_thread(Path(path).read_bytes)
            if parsed.scheme!='https': raise ZoteroError(502,'Unsupported Zotero attachment redirect')
            # Credentials are deliberately never forwarded to the storage host.
            async with httpx.AsyncClient(transport=self.transport,timeout=120,follow_redirects=True) as client:
                r=await client.get(url)
                if r.status_code!=200:raise ZoteroError(r.status_code,'Zotero attachment download failed')
        if not r.content.startswith(b'%PDF'):raise ZoteroError(422,'Attachment is not a PDF')
        return r.content
    async def upload(self,key,path,filename):
        content=Path(path).read_bytes();md5=hashlib.md5(content).hexdigest()
        suffix=f'/items/{self.safe_key(key)}/file';headers={'If-None-Match':'*'}
        r=await self.request('POST',suffix,data={'md5':md5,'filename':filename,'filesize':str(len(content)),'mtime':str(int(Path(path).stat().st_mtime*1000))},headers=headers)
        authorization=r.json()
        if authorization.get('exists'): return
        url=authorization['url'];parsed=urlparse(url)
        if parsed.scheme!='https' and not(self.local and parsed.hostname in ('127.0.0.1','localhost','::1')):raise ZoteroError(502,'Invalid upload authorization URL')
        body=authorization.get('prefix','').encode()+content+authorization.get('suffix','').encode()
        async with httpx.AsyncClient(transport=self.transport,timeout=120) as client:
            r=await client.post(url,content=body,headers={'Content-Type':authorization['contentType']})
            if r.status_code not in (200,201,204):raise ZoteroError(r.status_code,'Zotero PDF upload failed')
        await self.request('POST',suffix,data={'upload':authorization['uploadKey']},headers=headers)
