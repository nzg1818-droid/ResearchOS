from typing import Protocol
from dataclasses import dataclass, field

@dataclass
class ProviderStatus:
    connected: bool
    provider: str
    capabilities: list[str] = field(default_factory=list)
    server_id: str = ''
    version: int = 0
    message: str = ''

class HealthCapability(Protocol):
    async def health(self) -> ProviderStatus: ...

class ImportCapability(Protocol):
    async def collections(self) -> list[dict]: ...
    async def items(self, collection: str | None = None, since: int | None = None) -> list[dict]: ...

class ExportCapability(Protocol):
    async def create(self, data: dict) -> dict: ...
    async def update(self, key: str, version: int, patch: dict) -> dict: ...

class AttachmentCapability(Protocol):
    async def download(self, key: str) -> bytes: ...
    async def upload(self, key: str, path, filename: str) -> None: ...

class SyncCapability(ImportCapability, ExportCapability, Protocol):
    async def item(self, key: str) -> dict: ...
