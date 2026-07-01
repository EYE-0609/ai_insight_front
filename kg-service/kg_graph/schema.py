from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GraphNode:
    node_id: str
    node_type: str
    name: str
    aliases: list[str] = field(default_factory=list)
    normalized_name: str = ""
    source_refs: list[str] = field(default_factory=list)
    raw_mentions: list[str] = field(default_factory=list)
    normalization_method: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceChunk:
    chunk_id: str
    text: str
    source_url: str = ""
    source_title: str = ""
    source_grade: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RelationCandidate:
    rel_id: str
    head: str
    head_type: str
    relation: str
    tail: str
    tail_type: str
    evidence_refs: list[str] = field(default_factory=list)
    evidence_text: str = ""
    source_url: str = ""
    source_title: str = ""
    source_grade: str = ""
    relation_origin: str = ""
    relation_level: str = ""
    relation_name: str = ""
    field_name: str = ""
    field_value: str = ""
    direction: str = ""
    explanation: str = ""
    edge_kind: str = ""
    confidence: float = 0.0
    status: str = "rejected_or_insufficient"
    direction_uncertain: bool = False
    score_breakdown: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphPayload:
    task_profile: dict[str, Any] = field(default_factory=dict)
    graph_nodes: list[GraphNode] = field(default_factory=list)
    relation_candidates: list[RelationCandidate] = field(default_factory=list)
    graph_edges: list[RelationCandidate] = field(default_factory=list)
    company_edges: list[RelationCandidate] = field(default_factory=list)
    profile_edges: list[RelationCandidate] = field(default_factory=list)
    structural_edges: list[RelationCandidate] = field(default_factory=list)
    inter_company_relations: list[RelationCandidate] = field(default_factory=list)
    evidence_chunks: list[EvidenceChunk] = field(default_factory=list)
    normalization_index: list[dict[str, Any]] = field(default_factory=list)
    confidence_meta: dict[str, Any] = field(default_factory=dict)
    qa_index_hints: dict[str, Any] = field(default_factory=dict)
    persistence_meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
