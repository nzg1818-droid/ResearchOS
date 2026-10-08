"""The only resolver of ResearchOS-managed attachment paths."""
import hashlib
import re
from pathlib import Path, PurePosixPath
import shutil

class Storage:
    def __init__(self, root): self.root = Path(root).resolve()

    def resolve(self, relative):
        key = PurePosixPath(str(relative).replace('\\','/'))
        if key.is_absolute() or '..' in key.parts or ':' in str(key) or not key.parts or key.parts[0] != 'files':
            raise ValueError('Invalid managed file reference')
        result = (self.root / Path(*key.parts)).resolve()
        if not result.is_relative_to(self.root / 'files'):
            raise ValueError('Managed file escaped data root')
        return result

    @staticmethod
    def hash(path):
        with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

    def key(self, digest):
        if not re.fullmatch('[a-f0-9]{64}',digest): raise ValueError('Invalid PDF hash')
        return f'files/{digest}.pdf'

    def copy(self, source, digest):
        key = self.key(digest); destination = self.resolve(key)
        destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists() or self.hash(destination) != digest:
            temporary = destination.with_suffix('.tmp')
            shutil.copyfile(source, temporary)
            if self.hash(temporary) != digest:
                temporary.unlink(missing_ok=True)
                raise ValueError('Source PDF changed during import')
            temporary.replace(destination)
        return key
