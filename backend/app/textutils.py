import re
import unicodedata

def normalized(value):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', value or '').casefold())

def local_context(page_text, selected, radius=240):
    page_text = re.sub(r'\s+', ' ', page_text).strip()
    selected = re.sub(r'\s+', ' ', selected).strip()
    index = page_text.find(selected)
    if index < 0:
        return {'before': '', 'after': '', 'context': selected}
    before = page_text[max(0,index-radius):index]
    after = page_text[index+len(selected):index+len(selected)+radius]
    return {'before': before, 'after': after, 'context': before+selected+after}
