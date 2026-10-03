# MQTT Topic Guide

This document summarizes the MQTT data observed in the JSONL recordings and the meanings described in `FT-MQTT-doc`. It is intended as a compact reference for analysis and anomaly detection.

## Topic Layout

```text
/j1/txt/<controller>/...
ccu/<area>/<message>
module/v1/ff/<module-serial>/<message>
fts/v1/ff/<fts-serial>/<message>
```

Each recorded message has the general envelope:

```json
{
  "timestamp": "<capture time>",
  "topic": "<MQTT topic>",
  "payload": { "...": "..." }
}
```

The payload is normally an object. Some CCU order topics contain arrays. Payload fields are described by the overview file without retaining their values.

## Main Topic Families

### `j1`: controller, sensor, and dashboard data

`j1` contains data exposed by the controller or gateway, including sensor readings and factory/UI-facing information.

| Topic area | Purpose | Typical information |
|---|---|---|
| `/j1/txt/1/i/cam` | Camera stream | Camera data string and timestamp; observed as the most frequent stream |
| `/j1/txt/1/i/bme680` | Environmental sensor | Temperature, humidity, pressure, air-quality fields, timestamp |
| `/j1/txt/1/i/ldr` | Light sensor | Brightness/light readings and timestamp |
| `/j1/txt/1/i/broadcast` | Device announcement | Hardware/software identity and message text |
| `/j1/txt/1/f/i/order` | Factory/UI order information | Workpiece type, state, timestamp |
| `/j1/txt/1/f/i/stock` | Factory/UI stock information | Workpieces, locations, storage unit identifiers |
| `/j1/txt/1/f/i/config/hbw` | HBW configuration | Warehouse/configuration data and timestamp |
| `/j1/txt/1/f/o/order` | Factory/UI order output | Workpiece type and timestamp |

The exact units and semantics of some sensor abbreviations (`aq`, `gr`, `iaq`, `ldr`, etc.) are not defined clearly in the documentation. Treat them as signals whose normal ranges must be learned from the data.

### `ccu`: central control and coordination

The CCU topics describe global orchestration, orders, inventory, configuration, and system topology.

| Topic | Purpose |
|---|---|
| `ccu/pairing/state` | Connected modules and FTS transports, availability, versions, battery state, and last-known locations |
| `ccu/pairing/pair_fts` | Request to pair an FTS, identified by `serialNumber` |
| `ccu/order/request` | Request a production or storage order; commonly includes `type`, `orderType`, timestamp, and optionally `workpieceId` |
| `ccu/order/response` | CCU-generated order ID, type, production steps, and state |
| `ccu/order/active` | Array of currently active orders and their production steps |
| `ccu/order/completed` | Array of completed or cancelled orders |
| `ccu/state/stock` | Current workpiece inventory, location, storage unit, type, ID, and state |
| `ccu/state/config` | Production durations, parallel-order limit, and FTS charging threshold |
| `ccu/state/flows` | Configured production flows for workpiece types such as `BLUE`, `RED`, and `WHITE` |
| `ccu/state/layout` | Modules, intersections, and roads in the factory layout |
| `ccu/state/version-mismatch` | CCU version and modules with incompatible versions |

The documentation also mentions `ccu/order/cancel`, `ccu/global`, and `ccu/set/*`; these were not present in the analyzed recordings.

### `module`: production-module protocol

Module topics follow:

```text
module/v1/ff/<module-serial>/<message>
```

| Suffix | Direction | Meaning |
|---|---|---|
| `state` | Module to CCU | Current action, load, operating mode, order, and error state |
| `order` | CCU to module | Production command such as pick, mill, drill, fire, or drop |
| `instantAction` | CCU to module | Immediate action such as reset, calibration, or configuration |
| `connection` | Module to CCU | Connectivity and availability, including online/offline status |
| `factsheet` | Module to observers/CCU | Static capabilities, limits, and protocol features |

Important state fields include `serialNumber`, `orderId`, `orderUpdateId`, `actionState`/`actionStates`, `loads`, `metadata`, `operatingMode`, and `errors`. Factsheets commonly describe `moduleClass`, supported actions, parameters, and physical/protocol limits.

### `fts`: automated guided vehicles

FTS topics use the same suffix pattern:

```text
fts/v1/ff/<fts-serial>/<message>
```

- `state`: driving/navigation state, battery, load, node and edge progress, actions, and errors.
- `order`: navigation order containing nodes, edges, and actions.
- `instantAction`: immediate vehicle actions such as load handling, initial-position detection, or charging control.
- `connection`: connectivity and availability.
- `factsheet`: vehicle capabilities, geometry, load limits, navigation types, and protocol features.

Important FTS state fields include `orderId`, `orderUpdateId`, `lastNodeId`, `lastNodeSequenceId`, `driving`, `waitingForLoadHandling`, `batteryState`, `load`, `nodeStates`, `edgeStates`, `actionState`/`actionStates`, and `errors`.

## Common Payload Concepts

- `timestamp` or `ts`: source message time. The outer `timestamp` in the JSONL envelope is the recorded message time.
- `serialNumber`: device identity; useful for grouping and cross-checking messages.
- `orderId` and `orderUpdateId`: link commands, progress updates, and final results.
- `actionState`/`actionStates`: lifecycle of an action. Typical states are `WAITING`, `INITIALIZING`, `RUNNING`, `PAUSED`, `FINISHED`, or `FAILED`.
- `loads`/`load`: workpiece or transport load information. The singular/plural difference is protocol-family dependent and should be handled explicitly.
- `errors`: structured error information.
- `factsheet`: relatively static capability information; it should not change frequently.
- `type`, `orderType`, `moduleClass`, `agvClass`, and related fields classify workpieces, orders, modules, or vehicles. The overview records their field names, not their concrete values.

## Anomaly Detection

Use the topics together rather than analyzing each stream in isolation.

### Connectivity and timing

- Flag missing or unexpectedly delayed `connection` messages.
- Compare `module`/`fts` connection state with `ccu/pairing/state`.
- Learn a normal interval distribution per topic. Flag long gaps, unexpected bursts, or a changed median interval.
- Treat sensor streams differently: camera messages are sub-second, while environmental sensors are approximately minute-scale in these recordings.

### State and action consistency

- Detect invalid action transitions, actions stuck in `WAITING`, `INITIALIZING`, or `RUNNING`, and failed actions without a corresponding error.
- Check that `orderUpdateId` increases consistently for one `orderId`.
- Correlate `ccu/order/request`, `ccu/order/response`, module/FTS `order`, and subsequent `state` messages.
- Compare expected process durations with observed durations and configured production durations.b

### Vehicle, inventory, and quality checks

- For FTS, cross-check `driving`, node/edge progress, `waitingForLoadHandling`, battery level, and load state.
- Reconcile `ccu/state/stock` with module `loads` and FTS `load` to find missing, duplicated, or incorrectly located workpieces.
- Monitor battery percentage, voltage, charging state, and the configured charging threshold.
- Track quality-action results, especially unexpected changes in `PASSED`/`FAILED` outcomes.

### Schema and sensor checks

- Detect missing fields, new fields, unexpected nulls, type changes, and undocumented topic branches.
- Handle known schema variants such as `load` versus `loads` and `actionState` versus `actionStates`.
- Detect sensor flatlines, impossible ranges, abrupt changes, or disagreement between related measurements.

## Practical Workflow

1. Group messages by topic and device identifier.
2. Parse source time from `payload.timestamp` or `payload.ts` when available.
3. Build per-topic baselines for message intervals, field presence, state transitions, and process durations.
4. Correlate related records using `serialNumber`, `orderId`, `orderUpdateId`, action IDs, and workpiece IDs.
5. Report anomalies with the topic, device, identifier, timestamp, observed deviation, and related messages.

Some meanings remain implementation-specific: the exact `j1` sensor units, the `f/i` versus `f/o` distinction, `NodeRed` topic segments, and fields such as FTS `lastCode`. These should be treated as unknown dimensions until confirmed experimentally or by the system owner.


# Module IDs
SVR4H92774: DPS
SVR4H73901: HBW
SVR3QL1089: DRILL
SVR4H88474: MILL
SVR4H77011: AIQS
CHRG0: CHRG