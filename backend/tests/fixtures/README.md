# Deterministic paper-intelligence fixtures

`electrocatalysis-extraction-v1.json` is a synthetic schema example, not scientific evidence. Fixture chunk IDs are symbolic and must be mapped to actual parsed chunks before evidence validation. Unanchored fields deliberately remain unverified.

`test_intelligence.py::paper` generates a three-page text PDF with abstract, electrochemical measurement and ex-situ characterization text. Other tests generate no-text and damaged PDFs, mutate values/units, return invalid model output and simulate provider failures. `MockProvider` extracts only deterministic snippets/obvious mV candidates; it is clearly labeled and is not a research model.
