from pathlib import Path
import pymupdf

root=Path(__file__).resolve().parents[1]
out=root/'acceptance-data'/'demo'
out.mkdir(parents=True,exist_ok=True)
doc=pymupdf.open()
for number in range(1,4):
    page=doc.new_page()
    page.insert_text((60,70),'ResearchOS synthetic demonstration — not a research finding',fontsize=16)
    page.insert_text((60,110),f'Page {number}: Select this sentence and save it as evidence.')
    page.insert_text((60,140),'No experimental measurement is reported in this demo.')
doc.set_metadata({'title':'ResearchOS synthetic demonstration'})
doc.save(out/'ResearchOS-demo.pdf')
print(out/'ResearchOS-demo.pdf')
