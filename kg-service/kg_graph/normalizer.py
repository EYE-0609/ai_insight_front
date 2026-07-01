from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .schema import GraphNode

COMPANY_SUFFIXES = (
    "新能源科技股份有限公司",
    "股份有限公司",
    "有限责任公司",
    "有限公司",
    "集团股份有限公司",
    "集团有限公司",
    "集团",
    "Corp.",
    "Corporation",
    "Ltd.",
    "Limited",
    "Inc.",
)


def normalize_entities(nodes: list[GraphNode]) -> tuple[list[dict[str, Any]], list[GraphNode], dict[str, str]]:
    groups: "OrderedDict[str, GraphNode]" = OrderedDict()
    mention_to_id: dict[str, str] = {}
    normalized_mention_to_id: dict[tuple[str, str], str] = {}
    normalization_index: list[dict[str, Any]] = []

    for node in nodes:
        mentions = _node_mentions(node)
        existing_id = _find_existing_id(node.node_type, mentions, normalized_mention_to_id)
        canonical_name, method = _canonical_name(node)
        canonical_id = existing_id or _node_id(node.node_type, canonical_name)

        if canonical_id not in groups:
            groups[canonical_id] = GraphNode(
                node_id=canonical_id,
                node_type=node.node_type,
                name=canonical_name,
                aliases=[],
                normalized_name=canonical_name,
                source_refs=[],
                raw_mentions=[],
                normalization_method=method,
            )

        target = groups[canonical_id]
        _merge_unique(target.aliases, [value for value in node.aliases if value and value != canonical_name])
        _merge_unique(target.source_refs, node.source_refs)
        _merge_unique(target.raw_mentions, mentions)
        if node.name and node.name != canonical_name:
            _merge_unique(target.aliases, [node.name])

        for mention in mentions:
            if not mention:
                continue
            mention_to_id[mention] = canonical_id
            normalized_mention_to_id[(node.node_type, _normalize_match_text(mention))] = canonical_id
            normalization_index.append(
                {
                    "raw": mention,
                    "canonical_id": canonical_id,
                    "method": method if canonical_id == target.node_id else "alias_match",
                }
            )

    return _dedupe_index(normalization_index), list(groups.values()), mention_to_id


def canonicalize_company_name(name: str) -> str:
    compact = _strip_spaces(name)
    for suffix in COMPANY_SUFFIXES:
        if compact.endswith(suffix) and len(compact) > len(suffix):
            return compact[: -len(suffix)]
    return compact


def _canonical_name(node: GraphNode) -> tuple[str, str]:
    if node.node_type != "Company":
        name = _strip_spaces(node.normalized_name or node.name)
        return name, "exact"

    cjk_alias = next((alias for alias in node.aliases if _contains_cjk(alias)), "")
    if cjk_alias:
        return _strip_spaces(cjk_alias), "alias_match"

    stripped = canonicalize_company_name(node.normalized_name or node.name)
    method = "suffix_strip" if stripped != _strip_spaces(node.normalized_name or node.name) else "exact"
    return stripped, method


def _find_existing_id(node_type: str, mentions: list[str], normalized_mention_to_id: dict[tuple[str, str], str]) -> str:
    for mention in mentions:
        existing = normalized_mention_to_id.get((node_type, _normalize_match_text(mention)))
        if existing:
            return existing
    return ""


def _node_mentions(node: GraphNode) -> list[str]:
    values = [node.name, node.normalized_name, *node.aliases, *node.raw_mentions]
    return _unique_strings([_strip_spaces(value) for value in values if value])


def _node_id(node_type: str, name: str) -> str:
    return f"{node_type.lower()}:{name}"


def _strip_spaces(value: str) -> str:
    return "".join(str(value or "").replace("\u3000", " ").split())


def _normalize_match_text(value: str) -> str:
    return _strip_spaces(value).lower()


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def _merge_unique(target: list[str], values: list[str]) -> None:
    seen = set(target)
    for value in values:
        if value and value not in seen:
            target.append(value)
            seen.add(value)


def _unique_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _dedupe_index(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item["raw"], item["canonical_id"])
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result
