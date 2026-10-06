# Explicit demo fixtures

Run `../.venv/Scripts/python.exe generate.py` from this folder to create a three-page PDF under the gitignored acceptance-data directory. Import that PDF explicitly through Library if you want to explore annotation workflows offline. It contains clearly labeled synthetic text and a reserved example DOI.

No demo results are returned by production search. The unit tests contain deterministic HTTP metadata fixtures and separately generate 100 distinct test PDFs to exercise folder import.
