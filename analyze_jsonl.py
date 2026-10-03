"""Create a graph-friendly structural overview of JSON Lines telemetry files.

Examples:
    python analyze_jsonl.py "FT-data-20260612-original"
    python analyze_jsonl.py "FT-data-20260612-original\\*.jsonl" -o overview.json
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


CLASS_KEYS = {"class", "moduleClass", "agvClass", "orderType", "type", "subType"}
TIMESTAMP_KEYS = {"timestamp", "ts", "pairedSince", "lastSeen", "completedAt"}


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def iter_records(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}: invalid JSON on line {line_number}: {error.msg}") from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}: line {line_number} is not a JSON object")
            yield line_number, record


def json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def add_field(summary: dict[str, dict[str, Any]], path: str, value: Any) -> None:
    field = summary.setdefault(path, {"types": Counter(), "occurrences": 0, "class_values": Counter()})
    field["types"][json_type(value)] += 1
    field["occurrences"] += 1
    if path.rsplit(".", 1)[-1] in CLASS_KEYS and isinstance(value, (str, int, float, bool)):
        field["class_values"][str(value)] += 1
    if isinstance(value, dict):
        for key, nested_value in value.items():
            add_field(field.setdefault("children", {}), f"{path}.{key}", nested_value)
    elif isinstance(value, list):
        field["array_item_types"] = Counter(json_type(item) for item in value)
        for item in value:
            if isinstance(item, (dict, list)):
                add_field(field.setdefault("children", {}), f"{path}[]", item)


def flatten_fields(summary: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for path, field in summary.items():
        result[path] = field
        result.update(flatten_fields(field.get("children", {})))
    return result


def counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def finalize_fields(fields: dict[str, dict[str, Any]]) -> dict[str, Any]:
    finalized = {}
    for path, field in fields.items():
        result = {
            "occurrences": field["occurrences"],
            "types": counter_dict(field["types"]),
        }
        if field.get("class_values"):
            result["class_values"] = counter_dict(field["class_values"])
        if field.get("array_item_types"):
            result["array_item_types"] = counter_dict(field["array_item_types"])
        finalized[path] = result
    return finalized


def summarize_topic(records: list[dict[str, Any]]) -> dict[str, Any]:
    outer_times = [record["outer_time"] for record in records if record["outer_time"]]
    source_times = [record["source_time"] for record in records if record["source_time"]]
    fields: dict[str, dict[str, Any]] = {}
    payload_types = Counter(json_type(record.get("payload")) for record in records)
    for record in records:
        payload = record.get("payload")
        add_field(fields, "payload", payload)

    def time_stats(times: list[datetime]) -> dict[str, Any]:
        ordered = sorted(times)
        gaps = [(right - left).total_seconds() for left, right in zip(ordered, ordered[1:])]
        result: dict[str, Any] = {
            "first": ordered[0].isoformat() if ordered else None,
            "last": ordered[-1].isoformat() if ordered else None,
            "duration_seconds": (ordered[-1] - ordered[0]).total_seconds() if len(ordered) > 1 else 0,
        }
        if gaps:
            result["interval_seconds"] = {
                "minimum": min(gaps),
                "maximum": max(gaps),
                "mean": round(statistics.mean(gaps), 6),
                "median": statistics.median(gaps),
                "zero_gap_count": sum(gap == 0 for gap in gaps),
            }
        return result

    return {
        "occurrences": len(records),
        "payload_types": counter_dict(payload_types),
        "outer_timestamp": time_stats(outer_times),
        "source_timestamp": time_stats(source_times),
        "payload_fields": finalize_fields(flatten_fields(fields)),
        "source_timestamp_fields": counter_dict(Counter(record["source_field"] for record in records if record["source_field"])),
    }


def compact_topic_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Keep schema information while excluding observed payload values."""
    payload_fields = summary["payload_fields"]
    class_fields = [
        path for path, field in sorted(payload_fields.items()) if "class_values" in field
    ]
    outer = summary["outer_timestamp"]
    source = summary["source_timestamp"]
    outer_interval = outer.get("interval_seconds", {})
    return {
        "message_count": summary["occurrences"],
        "payload_shape": ", ".join(summary["payload_types"]),
        "payload_structure": build_payload_structure(payload_fields),
        "classification_fields": ", ".join(class_fields) or "none observed",
        "first_message": outer["first"],
        "last_message": outer["last"],
        "observation_duration_seconds": outer["duration_seconds"],
        "message_interval_seconds": {
            "minimum": outer_interval.get("minimum"),
            "maximum": outer_interval.get("maximum"),
            "average": outer_interval.get("mean"),
            "median": outer_interval.get("median"),
        },
        "payload_timestamp_fields": ", ".join(summary["source_timestamp_fields"]) or "none observed",
    }


def build_payload_structure(fields: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Turn field paths into readable name nodes without retaining field values."""
    structure: dict[str, Any] = {}
    for path, field in sorted(fields.items()):
        parts = path.split(".")
        current = structure
        for part in parts:
            if part.endswith("[]"):
                part = part[:-2]
                current = current.setdefault(part, {})
                current = current.setdefault("items", {})
            else:
                current = current.setdefault(part, {})
        current["_type"] = ", ".join(field["types"])
    return structure


def analyze(paths: list[Path]) -> dict[str, Any]:
    topics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        file_records = 0
        for line_number, record in iter_records(path):
            outer_time = parse_timestamp(record.get("timestamp"))
            payload = record.get("payload")
            source_field = None
            source_time = None
            if isinstance(payload, dict):
                for key in sorted(TIMESTAMP_KEYS):
                    candidate = parse_timestamp(payload.get(key))
                    if candidate:
                        source_field = key
                        source_time = candidate
                        break
            topic = str(record.get("topic", "<missing topic>"))
            topics[topic].append({"outer_time": outer_time, "source_time": source_time, "source_field": source_field, "payload": record.get("payload")})
            file_records += 1

    detailed_topic_summaries = {topic: summarize_topic(records) for topic, records in sorted(topics.items())}
    return build_topic_tree(detailed_topic_summaries)


def build_topic_tree(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build an occurrence-sorted tree from slash-separated topic names."""
    tree: dict[str, Any] = {}
    for topic, summary in summaries.items():
        current = tree
        segments = [segment for segment in topic.split("/") if segment]
        for segment in segments:
            current = current.setdefault(segment, {"_topic_occurrences": 0})
            current["_topic_occurrences"] += summary["occurrences"]
        current["_topic"] = topic
        current["_summary"] = compact_topic_summary(summary)

    def sort_branch(branch: dict[str, Any]) -> dict[str, Any]:
        children = []
        for name, value in branch.items():
            if name.startswith("_"):
                continue
            children.append((name, sort_branch(value), value.get("_topic_occurrences", 0)))
        children.sort(key=lambda item: (-item[2], item[0]))
        result: dict[str, Any] = {}
        for name, value, _ in children:
            result[name] = value
        for name, value in branch.items():
            if name.startswith("_"):
                result[name] = value
        return result

    return sort_branch(tree)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="JSONL files, directories, or glob patterns")
    parser.add_argument("-o", "--output", type=Path, default=Path("jsonl_overview.json"), help="output JSON path")
    return parser.parse_args()


def resolve_inputs(inputs: Iterable[Path]) -> list[Path]:
    paths = []
    for path in inputs:
        if path.is_dir():
            paths.extend(sorted(path.glob("*.jsonl")))
        elif path.is_file():
            paths.append(path)
        else:
            paths.extend(sorted(path.parent.glob(path.name)))
    return list(dict.fromkeys(path.resolve() for path in paths))


def main() -> None:
    args = parse_args()
    paths = resolve_inputs(args.inputs)
    if not paths:
        raise ValueError("No JSONL files found.")
    overview = analyze(paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(overview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Analyzed {len(paths)} file(s) and {len(overview)} top-level topic branches -> {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error