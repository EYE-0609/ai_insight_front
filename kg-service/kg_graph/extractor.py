from __future__ import annotations

import hashlib
import re
from typing import Any

from .relation_catalog import match_relation_template
from .schema import EvidenceChunk, GraphNode, RelationCandidate

DOWNSTREAM_KEYWORDS = ("下游", "客户", "供货", "供应给", "应用于", "销往", "整车")
UPSTREAM_KEYWORDS = ("上游", "供应商", "采购", "来自", "原材料")


def extract_nodes(insight_payload: dict[str, Any]) -> list[GraphNode]:
    nodes: list[GraphNode] = []
    task_profile = insight_payload.get("task_profile") or {}
    industry = str(task_profile.get("industry") or task_profile.get("query") or "").strip()
    profile_id = str(task_profile.get("profile_id") or "generic").strip()
    if industry:
        nodes.append(_node("Industry", industry))

    for segment in insight_payload.get("chain_skeleton") or []:
        segment_name = str(segment.get("segment") or "").strip()
        if segment_name:
            nodes.append(
                _node(
                    "Segment",
                    segment_name,
                    source_refs=list(segment.get("evidence_sources") or []),
                )
            )
        for subsegment in segment.get("subsegments") or []:
            subsegment_name = str(subsegment or "").strip()
            if subsegment_name:
                nodes.append(
                    _node(
                        "Subsegment",
                        subsegment_name,
                        source_refs=list(segment.get("evidence_sources") or []),
                    )
                )

    for segment in insight_payload.get("segment_companies") or []:
        for company in segment.get("companies") or []:
            company_name = str(company.get("company_name") or "").strip()
            if company_name:
                nodes.append(_node("Company", company_name, source_refs=list(company.get("evidence_sources") or [])))

    for card in insight_payload.get("company_cards") or []:
        company_name = str(card.get("company_name") or "").strip()
        if company_name:
            nodes.append(
                _node(
                    "Company",
                    company_name,
                    aliases=list(card.get("aliases") or []),
                    source_refs=_source_urls(card.get("key_sources") or []),
                )
            )
        subsegment = str(card.get("subsegment") or "").strip()
        if subsegment:
            nodes.append(_node("Subsegment", subsegment, source_refs=_source_urls(card.get("key_sources") or [])))
        for value in card.get("business_lines") or []:
            nodes.append(_node("BusinessLine", str(value).strip(), source_refs=_source_urls(card.get("key_sources") or [])))
        for value in card.get("product_lines") or []:
            nodes.append(_node("Product", str(value).strip(), source_refs=_source_urls(card.get("key_sources") or [])))
        for value in card.get("core_technologies") or []:
            nodes.append(_node("Technology", str(value).strip(), source_refs=_source_urls(card.get("key_sources") or [])))
        for clue in card.get("relationship_clues") or []:
            target_company = _parse_relationship_clue(str(clue or "").strip()).get("target_company", "")
            if target_company:
                nodes.append(_node("Company", target_company, source_refs=_source_urls(card.get("key_sources") or [])))

    for source in insight_payload.get("source_index") or []:
        url = str(source.get("url") or "").strip()
        if url:
            nodes.append(
                _node(
                    "Source",
                    url,
                    aliases=[str(source.get("title") or "").strip()] if source.get("title") else [],
                    source_refs=[url],
                )
            )

    return _dedupe_nodes(nodes)


def extract_evidence_chunks(insight_payload: dict[str, Any]) -> list[EvidenceChunk]:
    chunks: list[EvidenceChunk] = []
    for source in insight_payload.get("source_index") or []:
        text = str(source.get("snippet") or "").strip()
        if text:
            chunks.append(_chunk(text, source))

    for card in insight_payload.get("company_cards") or []:
        source = _first_source(card, insight_payload)
        for excerpt in card.get("evidence_excerpts") or []:
            text = str(excerpt or "").strip()
            if text:
                chunks.append(_chunk(text, source))
        for clue in card.get("relationship_clues") or []:
            text = str(clue or "").strip()
            if text:
                chunks.append(_chunk(text, source))
        for row in _iter_field_evidence_rows(card):
            if _is_valid_field_evidence_row(row):
                chunks.append(
                    _chunk(
                        str(row.get("evidence_text") or "").strip(),
                        {
                            "url": row.get("source_url"),
                            "title": row.get("source_title"),
                            "source_grade": row.get("source_grade"),
                        },
                    )
                )

    return _dedupe_chunks(chunks)


def extract_relation_candidates(
    insight_payload: dict[str, Any],
    mention_to_id: dict[str, str],
    evidence_chunks: list[EvidenceChunk],
) -> list[RelationCandidate]:
    relations: list[RelationCandidate] = []
    task_profile = insight_payload.get("task_profile") or {}
    industry = str(task_profile.get("industry") or task_profile.get("query") or "").strip()
    profile_id = str(task_profile.get("profile_id") or "generic").strip()
    industry_id = mention_to_id.get(industry, _node_id("Industry", industry)) if industry else ""

    for segment in insight_payload.get("chain_skeleton") or []:
        segment_name = str(segment.get("segment") or "").strip()
        segment_id = mention_to_id.get(segment_name, _node_id("Segment", segment_name))
        if industry_id and segment_name:
            relations.append(
                _relation(
                    head=industry_id,
                    head_type="Industry",
                    relation="industry_has_segment",
                    tail=segment_id,
                    tail_type="Segment",
                    evidence_text=str(segment.get("description") or segment_name),
                    source_url=_first_url(segment.get("evidence_sources") or []),
                    source_grade="",
                    relation_origin="structured_field",
                    edge_kind="structural",
                    evidence_chunks=evidence_chunks,
                )
            )
        for subsegment in segment.get("subsegments") or []:
            subsegment_name = str(subsegment or "").strip()
            if not subsegment_name:
                continue
            relations.append(
                _relation(
                    head=segment_id,
                    head_type="Segment",
                    relation="segment_has_subsegment",
                    tail=_node_id("Subsegment", subsegment_name),
                    tail_type="Subsegment",
                    evidence_text=str(segment.get("description") or subsegment_name),
                    source_url=_first_url(segment.get("evidence_sources") or []),
                    source_grade="",
                    relation_origin="structured_field",
                    edge_kind="structural",
                    evidence_chunks=evidence_chunks,
                )
            )

    for segment in insight_payload.get("segment_companies") or []:
        segment_name = str(segment.get("segment") or "").strip()
        segment_id = mention_to_id.get(segment_name, _node_id("Segment", segment_name))
        for company in segment.get("companies") or []:
            company_name = str(company.get("company_name") or "").strip()
            if not company_name:
                continue
            source_url = _first_url(company.get("evidence_sources") or [])
            relations.append(
                _relation(
                    head=mention_to_id.get(company_name, _node_id("Company", company_name)),
                    head_type="Company",
                    relation="company_in_segment",
                    tail=segment_id,
                    tail_type="Segment",
                    evidence_text=str(company.get("reason") or ""),
                    source_url=source_url,
                    source_grade="",
                    relation_origin="structured_field",
                    edge_kind="structural",
                    evidence_chunks=evidence_chunks,
                )
            )

    for card in insight_payload.get("company_cards") or []:
        company_name = str(card.get("company_name") or "").strip()
        if not company_name:
            continue
        company_id = mention_to_id.get(company_name, _node_id("Company", company_name))
        source = _first_source(card, insight_payload)
        source_url = str(source.get("url") or "").strip()
        source_grade = str(source.get("source_grade") or "").strip()

        subsegment = str(card.get("subsegment") or "").strip()
        if subsegment:
            relations.append(
                _relation(
                    head=company_id,
                    head_type="Company",
                    relation="company_in_subsegment",
                    tail=_node_id("Subsegment", subsegment),
                    tail_type="Subsegment",
                    evidence_text=_evidence_for_value(card, subsegment),
                    source_url=source_url,
                    source_title=str(source.get("title") or "").strip(),
                    source_grade=source_grade,
                    relation_origin="structured_field",
                    edge_kind="structural",
                    evidence_chunks=evidence_chunks,
                )
            )

        relations.extend(
            _profile_relations(
                card=card,
                company_id=company_id,
                field_name="business_lines",
                relation="company_has_business_line",
                tail_type="BusinessLine",
                source=source,
                evidence_chunks=evidence_chunks,
                mention_to_id=mention_to_id,
            )
        )
        relations.extend(
            _profile_relations(
                card=card,
                company_id=company_id,
                field_name="product_lines",
                relation="company_has_product",
                tail_type="Product",
                source=source,
                evidence_chunks=evidence_chunks,
                mention_to_id=mention_to_id,
            )
        )
        relations.extend(
            _profile_relations(
                card=card,
                company_id=company_id,
                field_name="core_technologies",
                relation="company_has_technology",
                tail_type="Technology",
                source=source,
                evidence_chunks=evidence_chunks,
                mention_to_id=mention_to_id,
            )
        )
        relations.extend(_relationship_clue_relations(card, company_id, mention_to_id, evidence_chunks, source, profile_id))

    return _dedupe_relations(relations)


def _profile_relations(
    card: dict[str, Any],
    company_id: str,
    field_name: str,
    relation: str,
    tail_type: str,
    source: dict[str, Any],
    evidence_chunks: list[EvidenceChunk],
    mention_to_id: dict[str, str],
) -> list[RelationCandidate]:
    result: list[RelationCandidate] = []
    for value in card.get(field_name) or []:
        name = str(value or "").strip()
        if not name:
            continue
        field_evidence = _field_evidence_for_value(card, field_name, name)
        evidence_text = field_evidence.get("evidence_text") or _evidence_for_value(card, name)
        source_url = field_evidence.get("source_url") or str(source.get("url") or "").strip()
        source_title = field_evidence.get("source_title") or str(source.get("title") or "").strip()
        source_grade = field_evidence.get("source_grade") or str(source.get("source_grade") or "").strip()
        result.append(
            _relation(
                head=company_id,
                head_type="Company",
                relation=relation,
                tail=_node_id(tail_type, name),
                tail_type=tail_type,
                evidence_text=evidence_text,
                source_url=source_url,
                source_title=source_title,
                source_grade=source_grade,
                relation_origin="explicit_evidence",
                edge_kind="profile",
                evidence_chunks=evidence_chunks,
                field_name=field_name,
                field_value=name,
            )
        )
    return result


def _relationship_clue_relations(
    card: dict[str, Any],
    company_id: str,
    mention_to_id: dict[str, str],
    evidence_chunks: list[EvidenceChunk],
    source: dict[str, Any],
    profile_id: str,
) -> list[RelationCandidate]:
    result: list[RelationCandidate] = []
    company_name = str(card.get("company_name") or "").strip()
    for clue in card.get("relationship_clues") or []:
        clue_text = str(clue or "").strip()
        parsed = _parse_relationship_clue(clue_text)
        if not parsed:
            continue
        target_company = parsed.get("target_company", "")
        if not target_company:
            continue
        target_id = mention_to_id.get(target_company, _node_id("Company", target_company))
        direction = _normalize_direction(parsed.get("direction", ""))
        head_id, tail_id = _orient_company_relation(company_id, target_id, direction)
        relation_name = parsed.get("relation_name", "")
        template = match_relation_template(relation_name, profile_id)
        relation_level = parsed.get("relation_level") or template["relation_level"]
        relation_key = template["relation_key"] if relation_level != "special" else "special_relation"
        source_url = parsed.get("source_url") or str(source.get("url") or "").strip()
        source_grade = parsed.get("source_grade") or str(source.get("source_grade") or "").strip()
        result.append(
            _relation(
                head=head_id,
                head_type="Company",
                relation=relation_key,
                tail=tail_id,
                tail_type="Company",
                evidence_text=parsed.get("evidence_text", ""),
                source_url=source_url,
                source_title=str(source.get("title") or "").strip(),
                source_grade=source_grade,
                relation_origin="card_structured",
                relation_level=relation_level,
                relation_name=relation_name or template["relation_label"],
                direction=direction,
                explanation=parsed.get("explanation", ""),
                edge_kind="company",
                evidence_chunks=evidence_chunks,
                direction_uncertain=direction == "unknown",
            )
        )
    return result


def _relation(
    head: str,
    head_type: str,
    relation: str,
    tail: str,
    tail_type: str,
    evidence_text: str,
    source_url: str,
    relation_origin: str,
    evidence_chunks: list[EvidenceChunk],
    source_title: str = "",
    source_grade: str = "",
    direction_uncertain: bool = False,
    relation_level: str = "",
    relation_name: str = "",
    direction: str = "",
    explanation: str = "",
    edge_kind: str = "",
    field_name: str = "",
    field_value: str = "",
) -> RelationCandidate:
    refs = _matching_chunk_ids(evidence_text, evidence_chunks)
    rel_id = _stable_id("rel", head, relation, tail, evidence_text)
    return RelationCandidate(
        rel_id=rel_id,
        head=head,
        head_type=head_type,
        relation=relation,
        tail=tail,
        tail_type=tail_type,
        evidence_refs=refs,
        evidence_text=evidence_text,
        source_url=source_url,
        source_title=source_title,
        source_grade=source_grade,
        relation_origin=relation_origin,
        relation_level=relation_level,
        relation_name=relation_name or relation,
        field_name=field_name,
        field_value=field_value,
        direction=direction,
        explanation=explanation,
        edge_kind=edge_kind,
        direction_uncertain=direction_uncertain,
    )


def _parse_relationship_clue(text: str) -> dict[str, str]:
    if "目标企业=" not in text or "关系名称=" not in text:
        return {}
    mapping = {
        "目标企业": "target_company",
        "关系层级": "relation_level",
        "关系名称": "relation_name",
        "方向": "direction",
        "证据": "evidence_text",
        "来源": "source_url",
        "来源等级": "source_grade",
        "解释": "explanation",
    }
    parsed: dict[str, str] = {}
    for part in re.split(r"[；;]\s*", text):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        normalized_key = mapping.get(key.strip())
        if normalized_key:
            parsed[normalized_key] = value.strip()
    return parsed


def _normalize_direction(value: str) -> str:
    text = str(value or "").strip()
    if text in {"本企业->目标企业", "本公司->目标企业", "head_to_tail"}:
        return "head_to_tail"
    if text in {"目标企业->本企业", "目标企业->本公司", "tail_to_head"}:
        return "tail_to_head"
    if text in {"双向", "互相", "bidirectional"}:
        return "bidirectional"
    return "unknown"


def _orient_company_relation(company_id: str, target_id: str, direction: str) -> tuple[str, str]:
    if direction == "tail_to_head":
        return target_id, company_id
    return company_id, target_id


def _evidence_for_value(card: dict[str, Any], value: str) -> str:
    for excerpt in card.get("evidence_excerpts") or []:
        text = str(excerpt or "").strip()
        if value and value in text:
            return text
    for source in card.get("key_sources") or []:
        snippet = str(source.get("snippet") or "").strip()
        if value and value in snippet:
            return snippet
    return str(value or "").strip()


def _field_evidence_for_value(card: dict[str, Any], field_name: str, value: str) -> dict[str, str]:
    expected = str(value or "").strip()
    for row in _iter_field_evidence_rows(card, field_name):
        if not _is_valid_field_evidence_row(row) or str(row.get("value") or "").strip() != expected:
            continue
        return {
            "evidence_text": str(row.get("evidence_text") or "").strip(),
            "source_url": str(row.get("source_url") or "").strip(),
            "source_title": str(row.get("source_title") or "").strip(),
            "source_grade": str(row.get("source_grade") or "").strip(),
        }
    return {}


def _is_valid_field_evidence_row(row: dict[str, Any]) -> bool:
    return bool(
        str(row.get("value") or "").strip()
        and str(row.get("evidence_text") or "").strip()
        and str(row.get("source_url") or "").strip()
    )


def _iter_field_evidence_rows(card: dict[str, Any], field_name: str = "") -> list[dict[str, Any]]:
    field_evidence = card.get("field_evidence") or {}
    if not isinstance(field_evidence, dict):
        return []
    if field_name:
        rows = field_evidence.get(field_name) or []
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    normalized = []
    for rows in field_evidence.values():
        if not isinstance(rows, list):
            continue
        normalized.extend(row for row in rows if isinstance(row, dict))
    return normalized


def _first_source(card: dict[str, Any], insight_payload: dict[str, Any]) -> dict[str, Any]:
    sources = card.get("key_sources") or []
    if sources:
        return sources[0]
    source_index = insight_payload.get("source_index") or []
    return source_index[0] if source_index else {}


def _source_urls(sources: list[dict[str, Any]]) -> list[str]:
    return [str(source.get("url") or "").strip() for source in sources if source.get("url")]


def _first_url(urls: list[Any]) -> str:
    return str(urls[0]).strip() if urls else ""


def _chunk(text: str, source: dict[str, Any]) -> EvidenceChunk:
    source_url = str(source.get("url") or "").strip()
    return EvidenceChunk(
        chunk_id=_stable_id("evidence", source_url, text),
        text=text,
        source_url=source_url,
        source_title=str(source.get("title") or "").strip(),
        source_grade=str(source.get("source_grade") or "").strip(),
    )


def _matching_chunk_ids(text: str, chunks: list[EvidenceChunk]) -> list[str]:
    if not text:
        return []
    return [chunk.chunk_id for chunk in chunks if text in chunk.text or chunk.text in text]


def _node(node_type: str, name: str, aliases: list[str] | None = None, source_refs: list[str] | None = None) -> GraphNode:
    cleaned_name = str(name or "").strip()
    return GraphNode(
        node_id=_node_id(node_type, cleaned_name),
        node_type=node_type,
        name=cleaned_name,
        aliases=[alias for alias in aliases or [] if alias],
        normalized_name=cleaned_name,
        source_refs=[ref for ref in source_refs or [] if ref],
        raw_mentions=[cleaned_name],
    )


def _node_id(node_type: str, name: str) -> str:
    return f"{node_type.lower()}:{name}"


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("||".join(str(part or "") for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _dedupe_nodes(nodes: list[GraphNode]) -> list[GraphNode]:
    result: list[GraphNode] = []
    seen: set[tuple[str, str, str]] = set()
    for node in nodes:
        key = (node.node_type, node.name, ",".join(node.aliases))
        if node.name and key not in seen:
            result.append(node)
            seen.add(key)
    return result


def _dedupe_chunks(chunks: list[EvidenceChunk]) -> list[EvidenceChunk]:
    result: list[EvidenceChunk] = []
    seen: set[str] = set()
    for chunk in chunks:
        if chunk.chunk_id not in seen:
            result.append(chunk)
            seen.add(chunk.chunk_id)
    return result


def _dedupe_relations(relations: list[RelationCandidate]) -> list[RelationCandidate]:
    result: list[RelationCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for relation in relations:
        key = (relation.head, relation.relation, relation.tail)
        if key not in seen:
            result.append(relation)
            seen.add(key)
    return result
