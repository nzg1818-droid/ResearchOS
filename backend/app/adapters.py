import asyncio
from typing import Protocol
from urllib.parse import quote
import httpx
import keyring
from tenacity import AsyncRetrying, stop_after_attempt, retry_if_exception_type, wait_exponential
from .schemas import Search, Hit
from .canonical import doi, normalized

class Transient(Exception):
    pass

class Adapter(Protocol):
    async def search(self, request: Search) -> list[Hit]: ...

async def get_json(client, url, params=None, headers=None):
    async for attempt in AsyncRetrying(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=12), retry=retry_if_exception_type((Transient, httpx.TransportError)), reraise=True):
        with attempt:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 429 or response.status_code >= 500:
                try:
                    delay = min(float(response.headers.get('Retry-After', '1')), 60)
                except ValueError:
                    delay = 2
                await asyncio.sleep(max(delay, 0))
                raise Transient(f'Provider temporarily unavailable (HTTP {response.status_code}); retry later')
            if response.status_code in (401, 403):
                raise ValueError('Provider denied access. Configure an API key in Settings or retry later.')
            response.raise_for_status()
            return response.json()

def exact(hits, request):
    hits = [h for h in hits if request.mode != 'title' or normalized(h.title) == normalized(request.query)]
    return [h for h in hits if (not request.start or (h.publication_date and h.publication_date >= str(request.start))) and (not request.end or (h.publication_date and h.publication_date <= str(request.end)))]

class Crossref:
    def __init__(self, client): self.client = client
    async def search(self, request):
        url = 'https://api.crossref.org/works'
        params = {'rows': request.limit}
        if request.mode == 'doi':
            url += '/' + quote(doi(request.query), safe='')
            params = {}
        else:
            params[{'keyword': 'query.bibliographic', 'title': 'query.title', 'author': 'query.author'}[request.mode]] = request.query
            filters = []
            if request.start: filters.append(f'from-pub-date:{request.start}')
            if request.end: filters.append(f'until-pub-date:{request.end}')
            if filters: params['filter'] = ','.join(filters)
        try:
            data = await get_json(self.client, url, params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404: return []
            raise
        items = [data['message']] if request.mode == 'doi' else data['message']['items']
        hits = []
        for item in items:
            parts = (item.get('published', {}).get('date-parts') or [[None]])[0]
            year = parts[0]
            published = '-'.join(f'{x:02d}' for x in (parts + [1, 1])[:3]) if year else None
            hits.append(Hit(source='crossref', source_id=item['DOI'], doi=item['DOI'], title=(item.get('title') or ['Untitled'])[0], authors=[' '.join(filter(None, [a.get('given'), a.get('family')])) or a.get('name', 'Unknown') for a in item.get('author', [])], year=year, publication_date=published, journal=(item.get('container-title') or [None])[0], publisher_url=item.get('resource', {}).get('primary', {}).get('URL') or item.get('URL'), citations=item.get('is-referenced-by-count'), raw=item))
        return exact(hits, request)

class OpenAlex:
    def __init__(self, client): self.client = client
    async def search(self, request):
        try: key = keyring.get_password('ResearchOS', 'openalex')
        except keyring.errors.KeyringError: key = None
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        params = {'per-page': request.limit}
        filters = []
        if request.start: filters.append(f'from_publication_date:{request.start}')
        if request.end: filters.append(f'to_publication_date:{request.end}')
        if request.mode == 'doi':
            filters.append('doi:https://doi.org/' + doi(request.query))
        elif request.mode == 'author':
            authors = await get_json(self.client, 'https://api.openalex.org/authors', {'search': request.query, 'per-page': 10}, headers)
            ids = [a['id'].rsplit('/', 1)[-1] for a in authors.get('results', [])]
            if not ids: return []
            filters.append('authorships.author.id:' + '|'.join(ids))
        elif request.mode == 'title':
            filters.append('title.search:' + request.query)
        else:
            params['search'] = request.query
        if filters: params['filter'] = ','.join(filters)
        data = await get_json(self.client, 'https://api.openalex.org/works', params, headers)
        hits = []
        for item in data.get('results', []):
            primary = item.get('primary_location') or {}
            locations = []
            for loc in item.get('locations', []):
                if loc.get('is_oa') and (loc.get('pdf_url') or loc.get('landing_page_url')):
                    locations.append({'pdf_url': loc.get('pdf_url'), 'url': loc.get('landing_page_url'), 'license': loc.get('license'), 'source': (loc.get('source') or {}).get('display_name'), 'is_oa': True})
            hits.append(Hit(source='openalex', source_id=item['id'], doi=item.get('doi'), title=item.get('title') or 'Untitled', authors=[a['author']['display_name'] for a in item.get('authorships', [])], year=item.get('publication_year'), publication_date=item.get('publication_date'), journal=(primary.get('source') or {}).get('display_name'), publisher_url=primary.get('landing_page_url'), citations=item.get('cited_by_count'), oa_locations=locations, raw=item))
        return exact(hits, request)

async def federated(request):
    async with httpx.AsyncClient(timeout=45, follow_redirects=True, headers={'User-Agent': 'ResearchOS/0.1 (local academic literature manager)'}) as client:
        adapters = {'crossref': Crossref(client), 'openalex': OpenAlex(client)}
        sources = list(dict.fromkeys(request.sources))
        results = await asyncio.gather(*(adapters[s].search(request) for s in sources), return_exceptions=True)
        hits, errors, counts = [], {}, {}
        for source, result in zip(sources, results):
            if isinstance(result, Exception):
                errors[source] = f'{type(result).__name__}: {str(result).split(" for url")[0]}'
            else:
                hits.extend(result)
                counts[source] = len(result)
        return hits, errors, counts
