"""Build and export the workpiece-aware filtered event log."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


MODULE_LABELS = {
    "SVR3QL1089": ("drilling station", "Drilling"),
    "SVR4H73901": ("HBW", "HBW"),
    "SVR4H77011": ("AIQS", "Quality inspection"),
    "SVR4H88474": ("milling station", "Milling"),
    "SVR4H92774": ("DPS", "DPS"),
}

LOCATION_LABELS = {
    "SVR3QL1089": "Drill",
    "DRILL": "Drill",
    "SVR4H73901": "HBW",
    "SVR4H77011": "AIQS",
    "SVR4H88474": "Mill",
    "MILL": "Mill",
    "SVR4H92774": "DPS",
}

ORDER_DESCRIPTIONS = {
    "SVR3QL1089": {
        "PICK": "receive the workpiece at the drilling station",
        "DRILL": "drill the workpiece",
        "DROP": "return the workpiece from the drilling station to the FTS",
    },
    "SVR4H73901": {
        "PICK": "store the workpiece in the HBW",
        "DROP": "retrieve the workpiece from the HBW",
    },
    "SVR4H77011": {
        "PICK": "receive the workpiece at the quality inspection station",
        "CHECK_QUALITY": "inspect the workpiece quality",
        "DROP": "return the workpiece from the quality inspection station to the FTS",
    },
    "SVR4H88474": {
        "PICK": "receive the workpiece at the milling station",
        "MILL": "mill the workpiece",
        "DROP": "return the workpiece from the milling station to the FTS",
    },
    "SVR4H92774": {
        "DROP": "introduce a raw workpiece into the factory at the DPS",
        "PICK": "ship the finished workpiece from the DPS",
        "INPUT_RGB": "read the workpiece color",
        "RGB_NFC": "read or write the workpiece NFC data",
    },
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
    "route",
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


def _location_label(location: str | None) -> str:
    if not location:
        return "Unknown"
    label = LOCATION_LABELS.get(location, location)
    return re.sub(r"[^A-Za-z0-9_-]+", "_", label).strip("_") or "Unknown"


def _order_activity(serial: str, command: str) -> str:
    description = ORDER_DESCRIPTIONS.get(serial, {}).get(command)
    if description is None:
        module_name = MODULE_LABELS.get(serial, (serial, serial))[0]
        command_name = command.replace("_", " ").lower()
        description = f"perform {command_name} at the {module_name}"
    return f"Order created: {description[0].upper()}{description[1:]}"


def _module_completion_activity(
    serial: str, command: str
) -> tuple[str, str] | None:
    if serial == "SVR4H73901":
        if command == "PICK":
            return "Workpiece stored in the HBW", "COMPLETE"
        if command == "DROP":
            return "Workpiece retrieved from the HBW", "COMPLETE"
        return None

    if serial == "SVR4H92774":
        if command == "DROP":
            return "Raw workpiece delivered to the FTS at the DPS", "COMPLETE"
        if command == "PICK":
            return "Finished workpiece shipped from the DPS", "COMPLETE"
        return None

    process_name = MODULE_LABELS[serial][1]
    if command == "PICK":
        return f"{process_name} started", "START"
    if command == "DROP":
        return f"{process_name} completed", "COMPLETE"
    return None


def _transport_start_activity(origin: str | None, destination: str | None) -> str:
    origin_label = _location_label(origin)
    destination_label = _location_label(destination)
    return f"Transport departed from {origin_label} to {destination_label}"


def _transport_end_activity(origin: str | None, destination: str | None) -> str:
    origin_label = _location_label(origin)
    destination_label = _location_label(destination)
    return f"Transport arrived at {destination_label} from {origin_label}"


def _load_objects(payload: dict[str, Any]) -> list[dict[str, Any]]:
    load = payload.get("load")
    if isinstance(load, dict):
        return [load]
    if isinstance(load, list):
        return [item for item in load if isinstance(item, dict)]
    return []


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict, set)):
        return False
    return bool(pd.isna(value))


def _append_route_node(trip: dict[str, Any], location: str | None) -> None:
    if location and location != trip["last_route_location"]:
        trip["route"].append(location)
        trip["last_route_location"] = location


def _unique_values(values: Iterable[Any]) -> list[Any]:
    unique: list[Any] = []
    for value in values:
        normalized = None if _is_missing(value) else value
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
    """Create normalized module events and per-workpiece FTS movement events."""
    events: list[dict[str, Any]] = []
    fts_driving: dict[str, bool] = {}
    fts_last_location: dict[str, str] = {}
    active_transports: dict[str, dict[str, Any]] = {}
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
        route: list[str] | None = None,
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
                "route": route,
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
                resource = serial

                if topic.endswith("/order"):
                    action = payload.get("action")
                    action = action if isinstance(action, dict) else {}
                    command = action.get("command") or _find_value(action, "type")
                    if command:
                        command_name = str(command).upper()
                        add_event(
                            record,
                            payload,
                            _order_activity(serial, command_name),
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
                        completion = _module_completion_activity(serial, command)
                        if completion is None:
                            continue
                        activity, lifecycle = completion
                        add_event(
                            record,
                            payload,
                            activity,
                            lifecycle,
                            resource,
                            action,
                        )

            elif topic.startswith("fts/v1/ff/"):
                resource = _find_value(payload, "serialNumber") or topic.split("/")[-2]
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
                    trip = active_transports.get(resource)
                    if trip is None:
                        origin = current_location or fts_last_location.get(resource)
                        workpieces = [
                            item
                            for item in _load_objects(payload)
                            if _find_value(item, "loadId")
                        ]
                        if workpieces:
                            trip_number += 1
                            route: list[str] = []
                            trip = {
                                "trip_id": f"{resource}:{trip_number}",
                                "origin": origin,
                                "route": route,
                                "last_route_location": origin,
                                "workpieces": workpieces,
                                "start_events": [],
                                "start_order_id": _find_value(payload, "orderId"),
                                "arrival_record": None,
                                "arrival_payload": None,
                                "arrival_location": None,
                            }
                            active_transports[resource] = trip
                            for load in workpieces:
                                event_count = len(events)
                                add_event(
                                    record,
                                    payload,
                                    _transport_start_activity(origin, None),
                                    "START",
                                    resource,
                                    piece_id=_find_value(load, "loadId"),
                                    piece_type=_find_value(load, "loadType"),
                                    trip_id=trip["trip_id"],
                                    origin=_location_label(origin),
                                    route=route,
                                    order_id=trip["start_order_id"],
                                )
                                if len(events) > event_count:
                                    trip["start_events"].append(events[-1])
                    elif trip is not None:
                        _append_route_node(trip, current_location)
                        trip["arrival_record"] = None
                        trip["arrival_payload"] = None
                        trip["arrival_location"] = None

                elif driving and resource in active_transports:
                    trip = active_transports[resource]
                    _append_route_node(trip, current_location)

                elif not driving and resource in active_transports:
                    trip = active_transports[resource]
                    if was_driving:
                        trip["arrival_record"] = record
                        trip["arrival_payload"] = payload
                        trip["arrival_location"] = current_location
                    if payload.get("waitingForLoadHandling") is True:
                        active_transports.pop(resource)
                        end_record = trip["arrival_record"] or record
                        end_payload = trip["arrival_payload"] or payload
                        destination = trip["arrival_location"] or current_location
                        if trip["route"] and trip["route"][-1] == destination:
                            trip["route"].pop()
                        if (
                            not trip["route"]
                            and _location_label(trip["origin"])
                            == _location_label(destination)
                        ):
                            start_event_ids = {
                                id(event) for event in trip["start_events"]
                            }
                            events[:] = [
                                event
                                for event in events
                                if id(event) not in start_event_ids
                            ]
                            arrived_ids: set[str] = set()
                        else:
                            trip["route"][:] = [
                                _location_label(node) for node in trip["route"]
                            ]
                            arrived_ids = {
                                _find_value(load, "loadId")
                                for load in _load_objects(end_payload)
                                if _find_value(load, "loadId")
                            }
                            for start_event in trip["start_events"]:
                                if start_event["workpiece_id"] in arrived_ids:
                                    start_event["destination"] = _location_label(
                                        destination
                                    )
                                    start_event["activity"] = _transport_start_activity(
                                        trip["origin"], destination
                                    )
                        for load in trip["workpieces"]:
                            piece_id = _find_value(load, "loadId")
                            if piece_id not in arrived_ids:
                                continue
                            add_event(
                                end_record,
                                end_payload,
                                _transport_end_activity(trip["origin"], destination),
                                "COMPLETE",
                                resource,
                                piece_id=piece_id,
                                piece_type=_find_value(load, "loadType"),
                                trip_id=trip["trip_id"],
                                origin=_location_label(trip["origin"]),
                                destination=_location_label(destination),
                                route=trip["route"],
                                order_id=(
                                    trip["start_order_id"]
                                    or _find_value(payload, "orderId")
                                ),
                            )
                    else:
                        _append_route_node(trip, current_location)

                if not driving and current_location:
                    fts_last_location[resource] = current_location
                fts_driving[resource] = driving

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
