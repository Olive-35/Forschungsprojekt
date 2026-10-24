"""Build and export the workpiece-aware filtered event log."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


MODULE_LABELS = {
    "SVR3QL1089": ("Drill", "Drilling"),
    "SVR4H73901": ("HBW", "HBW"),
    "SVR4H77011": ("Quality", "Quality"),
    "SVR4H88474": ("Mill", "Milling"),
    "SVR4H92774": ("RGB_NFC", "RGB_NFC"),
}

LOCATION_LABELS = {
    "SVR3QL1089": "Drill",
    "SVR4H73901": "HBW",
    "SVR4H77011": "Quality",
    "SVR4H88474": "Mill",
    "SVR4H92774": "RGB_NFC",
}

EVENT_COLUMNS = [
    "case_id",
    "activity",
    "timestamp",
    "resource",
    "source_topic",
    "lifecycle",
    "order_id",
    "workpiece_id",
    "workpiece_type",
    "source_line",
    "details",
    "FTS_Trip_ID",
    "origin",
    "destination",
]


def _payload_objects(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, dict):
        yield payload
    elif isinstance(payload, list):
        yield from (item for item in payload if isinstance(item, dict))


def _find_value(data: Any, key: str) -> str | None:
    if isinstance(data, dict):
        value = data.get(key)
        if value not in (None, "") and not isinstance(value, (dict, list)):
            return str(value)
        for child in data.values():
            found = _find_value(child, key)
            if found:
                return found
    elif isinstance(data, list):
        for child in data:
            found = _find_value(child, key)
            if found:
                return found
    return None


def _workpiece_id(data: Any, order_to_workpiece: dict[str, str]) -> str | None:
    piece_id = _find_value(data, "workpieceId") or _find_value(data, "loadId")
    order_id = _find_value(data, "orderId")
    if not piece_id and order_id:
        piece_id = order_to_workpiece.get(order_id)
    return piece_id


def _event_time(
    record: dict[str, Any],
    payload: dict[str, Any],
    action: dict[str, Any] | None = None,
) -> pd.Timestamp | pd.NaT:
    candidates = []
    if action:
        candidates.append(action.get("timestamp"))
    candidates.extend((payload.get("timestamp"), payload.get("ts"), record.get("timestamp")))
    for value in candidates:
        if value:
            parsed = pd.to_datetime(value, utc=True, errors="coerce")
            if not pd.isna(parsed):
                return parsed
    return pd.NaT


def _module_serial(topic: str, payload: dict[str, Any]) -> str:
    return _find_value(payload, "serialNumber") or topic.split("/")[-2]


def _route_destination(payload: dict[str, Any]) -> str | None:
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return None
    for node in reversed(nodes):
        if not isinstance(node, dict):
            continue
        action = node.get("action")
        if isinstance(action, dict) and str(action.get("type", "")).upper() == "DOCK":
            return str(node["id"]) if node.get("id") is not None else None
    for node in reversed(nodes):
        if isinstance(node, dict) and node.get("id") is not None:
            return str(node["id"])
    return None


def _location_label(location: str | None) -> str:
    if not location:
        return "Unknown"
    label = LOCATION_LABELS.get(location, location)
    return re.sub(r"[^A-Za-z0-9_-]+", "_", label).strip("_") or "Unknown"


def _unique_values(values: Iterable[Any]) -> list[Any]:
    unique: list[Any] = []
    for value in values:
        normalized = None if value is None or pd.isna(value) else value
        if normalized not in unique:
            unique.append(normalized)
    return unique


def _deduplicate_events(events: pd.DataFrame) -> pd.DataFrame:
    identity = [
        "case_id",
        "activity",
        "timestamp",
        "resource",
        "workpiece_id",
        "FTS_Trip_ID",
    ]
    merged_rows = []
    for _, group in events.groupby(identity, dropna=False, sort=False):
        row = group.iloc[0].to_dict()
        for column in events.columns:
            values = _unique_values(group[column].tolist())
            if column in {"source_line", "source_topic"} and len(values) > 1:
                row[column] = values
            elif len(values) > 1:
                row[column] = values
        merged_rows.append(row)
    return pd.DataFrame(merged_rows, columns=events.columns)


def build_filtered_event_log(
    ordered_records: Iterable[dict[str, Any]],
    case_id: str,
    order_to_workpiece: dict[str, str],
) -> pd.DataFrame:
    """Create normalized module events and per-workpiece FTS trip events."""
    events: list[dict[str, Any]] = []
    fts_routes: dict[str, dict[str, str | None]] = {}
    fts_driving: dict[str, bool] = {}
    fts_last_location: dict[str, str] = {}
    active_trips: dict[str, dict[str, Any]] = {}
    trip_number = 0

    def add_event(
        record: dict[str, Any],
        payload: dict[str, Any],
        activity: str,
        lifecycle: str | None,
        resource: str,
        action: dict[str, Any] | None = None,
        piece_id: str | None = None,
        piece_type: str | None = None,
        trip_id: str | None = None,
        origin: str | None = None,
        destination: str | None = None,
        order_id: str | None = None,
    ) -> None:
        timestamp = _event_time(record, payload, action)
        if pd.isna(timestamp):
            return
        event_payload = action or payload
        events.append(
            {
                "case_id": case_id,
                "activity": activity,
                "timestamp": timestamp,
                "resource": resource,
                "source_topic": record["topic"],
                "lifecycle": lifecycle,
                "order_id": order_id or _find_value(payload, "orderId"),
                "workpiece_id": piece_id or _workpiece_id(payload, order_to_workpiece),
                "workpiece_type": piece_type
                or _find_value(event_payload, "type")
                or _find_value(event_payload, "loadType"),
                "source_line": record.get("_source_line"),
                "details": json.dumps(
                    event_payload, ensure_ascii=False, separators=(",", ":")
                ),
                "FTS_Trip_ID": trip_id,
                "origin": origin,
                "destination": destination,
            }
        )

    for record in ordered_records:
        topic = record.get("topic", "")
        for payload in _payload_objects(record.get("payload")):
            if topic.startswith("module/v1/ff/"):
                serial = _module_serial(topic, payload)
                module_labels = MODULE_LABELS.get(serial)
                if not module_labels:
                    continue
                order_label, process_label = module_labels
                resource = serial

                if topic.endswith("/order"):
                    action = payload.get("action")
                    action = action if isinstance(action, dict) else {}
                    command = action.get("command") or _find_value(action, "type")
                    if command:
                        add_event(
                            record,
                            payload,
                            f"{order_label}_Order_Created",
                            "ORDERED",
                            resource,
                            action,
                        )
                elif topic.endswith("/state"):
                    actions = payload.get("actionStates", payload.get("actionState", []))
                    if isinstance(actions, dict):
                        actions = [actions]
                    if not isinstance(actions, list):
                        continue
                    for action in actions:
                        if not isinstance(action, dict):
                            continue
                        command = str(action.get("command", "")).upper()
                        state = str(action.get("state", "")).upper()
                        if state != "FINISHED":
                            continue
                        if command == "PICK":
                            activity = f"{process_label}_Process_Start"
                        elif command == "DROP":
                            activity = f"{process_label}_Process_End"
                        else:
                            continue
                        add_event(
                            record,
                            payload,
                            activity,
                            "START" if command == "PICK" else "COMPLETE",
                            resource,
                            action,
                        )

            elif topic.startswith("fts/v1/ff/"):
                resource = _find_value(payload, "serialNumber") or topic.split("/")[-2]
                if topic.endswith("/order"):
                    fts_routes[resource] = {
                        "order_id": _find_value(payload, "orderId"),
                        "destination": _route_destination(payload),
                    }
                    continue
                if not topic.endswith("/state"):
                    continue

                driving = payload.get("driving")
                if not isinstance(driving, bool):
                    continue
                last_node = payload.get("lastNodeId")
                current_location = (
                    str(last_node) if last_node not in (None, "") else None
                )
                was_driving = fts_driving.get(resource, False)

                if driving and not was_driving:
                    trip_number += 1
                    route = fts_routes.get(resource, {})
                    origin = current_location or fts_last_location.get(resource)
                    load = payload.get("load")
                    if isinstance(load, dict):
                        load = [load]
                    if not isinstance(load, list):
                        load = []
                    workpieces = [
                        item
                        for item in load
                        if isinstance(item, dict)
                        and _find_value(item, "loadId")
                    ]
                    active_trips[resource] = {
                        "trip_id": f"{resource}:{trip_number}",
                        "origin": origin,
                        "destination": route.get("destination"),
                        "order_id": route.get("order_id"),
                        "workpieces": workpieces,
                        "start_record": record,
                        "start_payload": payload,
                    }

                elif not driving and was_driving and resource in active_trips:
                    trip = active_trips.pop(resource)
                    destination = trip["destination"] or current_location
                    trip["end_record"] = record
                    trip["end_timestamp"] = _event_time(record, payload)
                    _append_trip_events(events, trip, destination, case_id)
                    if current_location:
                        fts_last_location[resource] = current_location

                if not driving and current_location:
                    fts_last_location[resource] = current_location
                fts_driving[resource] = driving

    for trip in active_trips.values():
        _append_trip_events(events, trip, trip["destination"], case_id, include_end=False)

    event_log = pd.DataFrame(events, columns=EVENT_COLUMNS)
    if event_log.empty:
        event_log["timestamp"] = pd.to_datetime(event_log["timestamp"], utc=True)
        return event_log
    event_log["timestamp"] = pd.to_datetime(
        event_log["timestamp"], utc=True, errors="coerce"
    )
    event_log = _deduplicate_events(event_log)
    return event_log.sort_values(
        ["timestamp"], kind="stable", na_position="last"
    ).reset_index(drop=True)


def _append_trip_events(
    events: list[dict[str, Any]],
    trip: dict[str, Any],
    destination: str | None,
    case_id: str,
    include_end: bool = True,
) -> None:
    origin = trip["origin"]
    activity = (
        f"Transporting_from_{_location_label(origin)}"
        f"_to_{_location_label(destination)}"
    )
    start_record = trip["start_record"]
    start_payload = trip["start_payload"]
    for load in trip["workpieces"]:
        piece_id = _find_value(load, "loadId")
        common = {
            "case_id": case_id,
            "activity": activity,
            "resource": _find_value(start_payload, "serialNumber"),
            "source_topic": start_record["topic"],
            "order_id": trip["order_id"],
            "workpiece_id": piece_id,
            "workpiece_type": _find_value(load, "loadType"),
            "FTS_Trip_ID": trip["trip_id"],
            "origin": origin,
            "destination": destination,
        }
        details = json.dumps(
            {"load": load, "FTS_Trip_ID": trip["trip_id"]},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        events.append(
            {
                **common,
                "timestamp": _event_time(start_record, start_payload),
                "lifecycle": "START",
                "source_line": start_record.get("_source_line"),
                "details": details,
            }
        )
        if include_end:
            events.append(
                {
                    **common,
                    "timestamp": trip["end_timestamp"],
                    "lifecycle": "COMPLETE",
                    "source_topic": trip["end_record"]["topic"],
                    "source_line": trip["end_record"].get("_source_line"),
                    "details": details,
                }
            )


def export_filtered_xes(event_log: pd.DataFrame, output_path: Path, case_id: str) -> None:
    """Write the transformed events as a single-trace XES file."""
    namespace = "http://www.xes-standard.org/"
    ET.register_namespace("", namespace)
    qname = lambda name: f"{{{namespace}}}{name}"
    log = ET.Element(
        qname("log"),
        {"xes.version": "1.0", "xes.features": "nested-attributes"},
    )
    for prefix, name, uri in [
        ("concept", "Concept", "http://www.xes-standard.org/concept.xesext"),
        ("time", "Time", "http://www.xes-standard.org/time.xesext"),
        ("lifecycle", "Lifecycle", "http://www.xes-standard.org/lifecycle.xesext"),
        ("org", "Organizational", "http://www.xes-standard.org/org.xesext"),
    ]:
        ET.SubElement(log, qname("extension"), {"name": name, "prefix": prefix, "uri": uri})
    ET.SubElement(log, qname("string"), {"key": "concept:name", "value": output_path.stem})
    ET.SubElement(log, qname("classifier"), {"name": "Activity", "keys": "concept:name"})

    trace = ET.SubElement(log, qname("trace"))
    ET.SubElement(trace, qname("string"), {"key": "concept:name", "value": case_id})
    xes_keys = {
        "activity": "concept:name",
        "timestamp": "time:timestamp",
        "resource": "org:resource",
        "lifecycle": "lifecycle:transition",
    }
    for _, event in event_log.iterrows():
        xes_event = ET.SubElement(trace, qname("event"))
        for column, value in event.items():
            if column == "case_id" or value is None or (
                not isinstance(value, (list, tuple, dict)) and pd.isna(value)
            ):
                continue
            key = xes_keys.get(column, column)
            if isinstance(value, (list, tuple, dict)):
                tag, text = "string", json.dumps(
                    value, ensure_ascii=False, separators=(",", ":")
                )
            elif column == "timestamp":
                tag, text = "date", value.isoformat().replace("+00:00", "Z")
            elif column == "source_line":
                tag, text = "int", str(int(value))
            else:
                tag, text = "string", str(value)
            ET.SubElement(xes_event, qname(tag), {"key": key, "value": text})

    ET.indent(log, space="  ")
    ET.ElementTree(log).write(output_path, encoding="utf-8", xml_declaration=True)
