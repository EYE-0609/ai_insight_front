from __future__ import annotations

import re

from .schema import EvidenceChunk, RelationCandidate

RULE_VERSION = "v1.0"


def apply_confidence(relation: RelationCandidate, evidence_chunks: list[EvidenceChunk]) -> RelationCandidate:
    score, breakdown = score_relation(relation, evidence_chunks)
    relation.confidence = score
    relation.status = bucket_status(score)
    relation.score_breakdown = breakdown
    return relation


def score_relation(relation: RelationCandidate, evidence_chunks: list[EvidenceChunk]) -> tuple[float, dict[str, float | str]]:
    breakdown: dict[str, float | str] = {"base": 0.50}
    score = 0.50
    source_grade = _source_grade(relation, evidence_chunks)

    if source_grade == "A":
        score += 0.15
        breakdown["source_grade"] = 0.15
    elif source_grade == "B":
        score += 0.08
        breakdown["source_grade"] = 0.08
    else:
        breakdown["source_grade"] = 0.0

    if _evidence_mentions_relation(relation):
        score += 0.10
        breakdown["explicit_evidence"] = 0.10
    else:
        breakdown["explicit_evidence"] = 0.0

    if _has_multiple_source_urls(relation, evidence_chunks):
        score += 0.08
        breakdown["multi_source"] = 0.08
    else:
        breakdown["multi_source"] = 0.0

    if _is_normalized(relation.head) and _is_normalized(relation.tail):
        score += 0.05
        breakdown["entity_normalized"] = 0.05
    else:
        breakdown["entity_normalized"] = 0.0

    if _has_recent_year(relation.source_title) or _has_recent_year(relation.source_url):
        score += 0.05
        breakdown["freshness"] = 0.05
    else:
        breakdown["freshness"] = 0.0

    cap, cap_reason = _hard_cap(relation, source_grade)
    if score > cap:
        score = cap
    breakdown["hard_cap"] = cap
    breakdown["hard_cap_reason"] = cap_reason
    return round(score, 4), breakdown


def bucket_status(score: float) -> str:
    if score >= 0.85:
        return "verified"
    if score >= 0.70:
        return "strong_candidate"
    if score >= 0.55:
        return "weak_candidate"
    return "rejected_or_insufficient"


def _hard_cap(relation: RelationCandidate, source_grade: str) -> tuple[float, str]:
    cap = 1.0
    reasons: list[str] = []
    if not relation.evidence_text.strip():
        cap = min(cap, 0.20)
        reasons.append("missing_evidence_text")
    if not relation.source_url.strip():
        cap = min(cap, 0.30)
        reasons.append("missing_source_url")
    if source_grade == "C":
        cap = min(cap, 0.55)
        reasons.append("c_grade_only")
    if relation.relation_origin == "inferred":
        cap = min(cap, 0.65)
        reasons.append("inferred_relation")
    if relation.relation_level == "special" and not relation.explanation.strip():
        cap = min(cap, 0.55)
        reasons.append("special_relation_missing_explanation")
    if not (_is_normalized(relation.head) and _is_normalized(relation.tail)):
        cap = min(cap, 0.60)
        reasons.append("unnormalized_entity")
    if relation.direction_uncertain:
        cap = min(cap, 0.65)
        reasons.append("direction_uncertain")
    return cap, ",".join(reasons) or "none"


def _source_grade(relation: RelationCandidate, evidence_chunks: list[EvidenceChunk]) -> str:
    if relation.source_grade:
        return relation.source_grade
    grades = [chunk.source_grade for chunk in evidence_chunks if chunk.chunk_id in relation.evidence_refs and chunk.source_grade]
    if "A" in grades:
        return "A"
    if "B" in grades:
        return "B"
    if "C" in grades:
        return "C"
    return ""


def _has_multiple_source_urls(relation: RelationCandidate, evidence_chunks: list[EvidenceChunk]) -> bool:
    ref_ids = set(relation.evidence_refs)
    source_urls = {
        chunk.source_url.strip()
        for chunk in evidence_chunks
        if chunk.chunk_id in ref_ids and chunk.source_url.strip()
    }
    return len(source_urls) >= 2


def _evidence_mentions_relation(relation: RelationCandidate) -> bool:
    evidence = relation.evidence_text or ""
    head_name = _id_name(relation.head)
    tail_name = _id_name(relation.tail)
    return bool(head_name and tail_name and head_name in evidence and tail_name in evidence)


def _is_normalized(entity_id: str) -> bool:
    return ":" in entity_id and bool(entity_id.split(":", 1)[1].strip())


def _id_name(entity_id: str) -> str:
    return entity_id.split(":", 1)[1] if ":" in entity_id else entity_id


def _has_recent_year(value: str) -> bool:
    for match in re.findall(r"(20\d{2})", value or ""):
        if int(match) >= 2025:
            return True
    return False
