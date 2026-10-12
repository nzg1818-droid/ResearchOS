"""Versioned strict extraction contract. Missing values stay null."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
SCHEMA_VERSION = 'paper-intelligence-1'
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
class Citation(Strict):
    chunk_id: str
    quote: str
    page: int | None = None
class Value(Strict):
    value: str | float | int | None = None
    origin: Literal['source_reported','app_computed','ai_interpretation'] = 'source_reported'
    confidence: float = Field(default=0.0, ge=0, le=1)
    evidence: list[Citation] = Field(default_factory=list)
    formula: str | None = None
    inputs: dict[str, float] = Field(default_factory=dict)
class MaterialRecord(Strict):
    canonical_name: Value = Field(default_factory=Value)
    composition: Value = Field(default_factory=Value)
    dopants: Value = Field(default_factory=Value)
    support: Value = Field(default_factory=Value)
    morphology: Value = Field(default_factory=Value)
    phase: Value = Field(default_factory=Value)
    structural_order: Value = Field(default_factory=Value)
    interface: Value = Field(default_factory=Value)
    role: Value = Field(default_factory=Value)
class SynthesisRecord(Strict):
    method: Value = Field(default_factory=Value)
    precursors: Value = Field(default_factory=Value)
    concentrations: Value = Field(default_factory=Value)
    solvent: Value = Field(default_factory=Value)
    potential: Value = Field(default_factory=Value)
    current: Value = Field(default_factory=Value)
    current_density: Value = Field(default_factory=Value)
    reference_electrode: Value = Field(default_factory=Value)
    time: Value = Field(default_factory=Value)
    temperature: Value = Field(default_factory=Value)
    pressure: Value = Field(default_factory=Value)
    atmosphere: Value = Field(default_factory=Value)
    ph: Value = Field(default_factory=Value)
    annealing: Value = Field(default_factory=Value)
    phosphidation: Value = Field(default_factory=Value)
    sulfidation: Value = Field(default_factory=Value)
    nitridation: Value = Field(default_factory=Value)
    scale: Value = Field(default_factory=Value)
    notes: Value = Field(default_factory=Value)
class CharacterizationRecord(Strict):
    method: Value = Field(default_factory=Value)
    mode: Value = Field(default_factory=Value)
    sample_state: Value = Field(default_factory=Value)
    finding: Value = Field(default_factory=Value)
    mechanism_relevance: Value = Field(default_factory=Value)
class ElectrochemistryRecord(Strict):
    reaction: Value = Field(default_factory=Value)
    cell_type: Value = Field(default_factory=Value)
    electrolyte: Value = Field(default_factory=Value)
    koh_original: Value = Field(default_factory=Value)
    koh_normalized: Value = Field(default_factory=Value)
    temperature: Value = Field(default_factory=Value)
    pressure: Value = Field(default_factory=Value)
    flow: Value = Field(default_factory=Value)
    working_electrode: Value = Field(default_factory=Value)
    counter_electrode: Value = Field(default_factory=Value)
    reference_electrode: Value = Field(default_factory=Value)
    reference_conversion: Value = Field(default_factory=Value)
    geometric_area: Value = Field(default_factory=Value)
    loading: Value = Field(default_factory=Value)
    normalization_basis: Value = Field(default_factory=Value)
    ir_correction: Value = Field(default_factory=Value)
    ir_percentage: Value = Field(default_factory=Value)
    ir_method: Value = Field(default_factory=Value)
    scan_rate: Value = Field(default_factory=Value)
    rotation: Value = Field(default_factory=Value)
class PerformanceRecord(Strict):
    metric: Value = Field(default_factory=Value)
    reported_value: Value = Field(default_factory=Value)
    reported_unit: Value = Field(default_factory=Value)
    normalized_value: Value = Field(default_factory=Value)
    normalized_unit: Value = Field(default_factory=Value)
    current_density: Value = Field(default_factory=Value)
    potential: Value = Field(default_factory=Value)
    overpotential: Value = Field(default_factory=Value)
    cell_voltage: Value = Field(default_factory=Value)
    duration: Value = Field(default_factory=Value)
    product: Value = Field(default_factory=Value)
    faradaic_efficiency: Value = Field(default_factory=Value)
    selectivity: Value = Field(default_factory=Value)
    yield_conversion: Value = Field(default_factory=Value)
    tafel_slope: Value = Field(default_factory=Value)
    rct: Value = Field(default_factory=Value)
    cdl_ecsa: Value = Field(default_factory=Value)
    retention: Value = Field(default_factory=Value)
    normalization_basis: Value = Field(default_factory=Value)
    condition_reference: Value = Field(default_factory=Value)
class MechanismRecord(Strict):
    claim: Value = Field(default_factory=Value)
    evidence_types: Value = Field(default_factory=Value)
    supporting_characterization: Value = Field(default_factory=Value)
    dft: Value = Field(default_factory=Value)
    kinetics: Value = Field(default_factory=Value)
    sample_state: Value = Field(default_factory=Value)
    limitation: Value = Field(default_factory=Value)
class PaperExtraction(Strict):
    one_minute_brief: Value = Field(default_factory=Value)
    research_question: Value = Field(default_factory=Value)
    study_objective: Value = Field(default_factory=Value)
    paper_type: Value = Field(default_factory=Value)
    highlights: Value = Field(default_factory=Value)
    limitations: Value = Field(default_factory=Value)
    unresolved_questions: Value = Field(default_factory=Value)
    industrial_relevance: Value = Field(default_factory=Value)
    materials: list[MaterialRecord] = Field(default_factory=list, max_length=100)
    synthesis: list[SynthesisRecord] = Field(default_factory=list, max_length=100)
    characterization: list[CharacterizationRecord] = Field(default_factory=list, max_length=100)
    electrochemistry: list[ElectrochemistryRecord] = Field(default_factory=list, max_length=100)
    performance: list[PerformanceRecord] = Field(default_factory=list, max_length=100)
    mechanism: list[MechanismRecord] = Field(default_factory=list, max_length=100)

def fields(payload, prefix=''):
    if isinstance(payload, dict):
        if 'value' in payload and 'evidence' in payload:
            yield prefix, payload
        else:
            for key, value in payload.items():
                yield from fields(value, f'{prefix}.{key}' if prefix else key)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            yield from fields(value, f'{prefix}.{index}')

class PaperAnswer(Strict):
    answer: str = Field(max_length=20000)
    citations: list[Citation] = Field(default_factory=list,max_length=12)
