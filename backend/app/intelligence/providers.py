"""Provider boundary: credentials remain in keyring; errors never echo responses."""
from dataclasses import dataclass
from typing import Protocol, Literal
from urllib.parse import urlsplit
import json
import re
import httpx
import keyring
from pydantic import BaseModel, Field, SecretStr, field_validator

SERVICE = 'ResearchOS.AI'
class ProviderError(Exception): pass
class ProviderInput(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    provider_type: Literal['openai-compatible','ollama','mock']
    endpoint: str = ''
    model: str = Field(min_length=1,max_length=150)
    max_output_tokens: int = Field(default=4000,ge=128,le=32000)
    timeout: int = Field(default=60,ge=5,le=300)
    concurrency: int = Field(default=2,ge=1,le=8)
    enabled: bool = True
    is_default: bool = False
    default_level: Literal['metadata','abstract','full_text'] = 'abstract'
    key: SecretStr | None = None

def validate_endpoint(kind, endpoint):
    if kind == 'mock': return ''
    p = urlsplit(endpoint)
    if p.username or p.password or p.query or p.fragment or not p.hostname:
        raise ValueError('Endpoint must not contain credentials, query or fragment')
    if kind == 'ollama':
        if p.scheme != 'http' or p.hostname not in ('localhost','127.0.0.1','::1'):
            raise ValueError('Ollama requires a loopback HTTP endpoint')
    elif p.scheme != 'https': raise ValueError('Remote providers require HTTPS')
    return endpoint.rstrip('/')

@dataclass
class Result:
    content: dict
    usage: dict
class LLMProvider(Protocol):
    async def health(self) -> dict: ...
    async def structured(self, system: str, payload: dict, schema: dict) -> Result: ...
    async def answer(self, system: str, payload: dict) -> Result: ...

class HTTPProvider:
    def __init__(self, config, transport=None):
        self.config=config;self.transport=transport
        self.endpoint=validate_endpoint(config.provider_type,config.endpoint)
    async def request(self, method, path, **kwargs):
        secret=keyring.get_password(SERVICE,str(self.config.id))
        headers={'Authorization':'Bearer '+secret} if secret else {}
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=self.config.timeout, follow_redirects=False, trust_env=self.config.provider_type!='ollama') as client:
                r=await client.request(method,self.endpoint+path,headers=headers,**kwargs)
        except httpx.TimeoutException: raise ProviderError('Provider timeout') from None
        except httpx.HTTPError: raise ProviderError('Provider connection failed') from None
        if r.status_code in (401,403):raise ProviderError('Provider auth error; update the key in AI settings')
        if r.status_code==429:raise ProviderError('Provider rate limit; retry later')
        if r.status_code>=300:raise ProviderError('Provider request failed ('+str(r.status_code)+')')
        if secret and secret in r.text:raise ProviderError('Provider response contained credential material and was discarded')
        try:return r.json()
        except ValueError:raise ProviderError('Invalid structured output') from None
    async def health(self):
        d=await self.request('GET','/api/tags' if self.config.provider_type=='ollama' else '/models')
        models=[m.get('name',m.get('id')) for m in d.get('models',d.get('data',[]))]
        return {'ok':self.config.model in models,'model':self.config.model,'message':'Connected; model listed' if self.config.model in models else 'Connected, but configured model was not listed'}
    async def structured(self,system,payload,schema):
        messages=[{'role':'system','content':system+'\nRequired JSON schema: '+json.dumps(schema)},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]
        if self.config.provider_type=='ollama':
            d=await self.request('POST','/api/chat',json={'model':self.config.model,'messages':messages,'stream':False,'think':False,'format':schema,'options':{'num_predict':self.config.max_output_tokens,'temperature':0}})
            raw=d.get('message',{}).get('content','');usage={k:d[k] for k in ('prompt_eval_count','eval_count') if k in d}
        else:
            d=await self.request('POST','/chat/completions',json={'model':self.config.model,'messages':messages,'max_tokens':self.config.max_output_tokens,'temperature':0,'response_format':{'type':'json_object'}})
            try:raw=d['choices'][0]['message']['content']
            except (KeyError,IndexError,TypeError):raise ProviderError('Invalid structured output') from None
            usage={k:v for k,v in d.get('usage',{}).items() if k in ('prompt_tokens','completion_tokens','total_tokens') and isinstance(v,int)}
        try:return Result(json.loads(raw),usage)
        except (TypeError,ValueError):raise ProviderError('Invalid structured output') from None
    async def answer(self,system,payload):
        from .schema import PaperAnswer
        return await self.structured(system,payload,PaperAnswer.model_json_schema())

class OpenAICompatibleProvider(HTTPProvider): pass
class OllamaProvider(HTTPProvider): pass
class MockProvider:
    async def health(self):return {'ok':True,'message':'Deterministic local mock; not a research model'}
    async def structured(self,system,payload,schema):
        chunks=payload.get('chunks',[]);section=payload.get('section','research_question')
        def value(c, v):return {'value':v,'confidence':0.8,'evidence':[{'chunk_id':c['id'],'page':c['page'],'quote':c['text']}]}
        if section=='performance':
            for c in chunks:
                m=re.search(r'(\d+(?:\.\d+)?)\s*mV',c['text'])
                if m:return Result({'performance':[{'metric':value(c,'overpotential'),'reported_value':value(c,float(m[1])),'reported_unit':value(c,'mV')}]},{})
        if section in ('one_minute_brief','research_question','highlights','limitations') and chunks:
            return Result({section:value(chunks[0],chunks[0]['text'])},{})
        return Result({}, {})
    async def answer(self,system,payload):
        chunks=payload.get('chunks',[])
        if not chunks:return Result({'answer':'Not found in this paper','citations':[]},{})
        c=chunks[0];return Result({'answer':c['text'],'citations':[{'chunk_id':c['id'],'page':c['page'],'quote':c['text']}]},{})

def provider(config,transport=None):
    if not config or not config.enabled:raise ProviderError('Provider not configured or disabled')
    return {'mock':MockProvider,'ollama':OllamaProvider,'openai-compatible':OpenAICompatibleProvider}[config.provider_type]() if config.provider_type=='mock' else {'ollama':OllamaProvider,'openai-compatible':OpenAICompatibleProvider}[config.provider_type](config,transport)
