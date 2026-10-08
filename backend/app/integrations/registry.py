"""Non-secret provider metadata and OS-backed credentials."""
import keyring
from .zotero import ZoteroLocal, ZoteroWeb

SERVICE='ResearchOS.Zotero'
def credential_name(library):return library.identity
def set_secret(library,value):
    if value:keyring.set_password(SERVICE,credential_name(library),value)
    else:
        try:keyring.delete_password(SERVICE,credential_name(library))
        except keyring.errors.PasswordDeleteError:pass
def adapter(library,transport=None):
    key=keyring.get_password(SERVICE,credential_name(library))
    if library.mode=='local':return ZoteroLocal(library.endpoint,library.library_type,library.library_id,key,server_id=library.server_id,transport=transport)
    return ZoteroWeb(library.library_type,library.library_id,key,transport=transport)
