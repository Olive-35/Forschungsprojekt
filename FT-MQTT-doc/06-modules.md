# 6. Module-Specific Documentation

## Table of Contents
- [6.1 Overview of All Modules](#61-overview-of-all-modules)
- [6.2 Common Topics for All Modules](#62-common-topics-for-all-modules)
- [6.3 Common Commands](#63-common-commands)
- [6.4 Module-Specific Processing Commands](#64-module-specific-processing-commands)
- [6.5 Operating Modes](#65-operating-modes)
- [6.6 Availability States](#66-availability-states)
- [6.7 Error Handling](#67-error-handling)
- [6.8 Typical Action Sequence](#68-typical-action-sequence)
- [6.9 Module Documentation Links](#69-module-documentation-links)

## 6.1 Overview of All Modules

The APS consists of eight distinct module types, each serving a specific role in the production process.

### Production Module Summary

| Module | Type | Primary Function | Commands Supported |
|--------|------|------------------|-------------------|
| [**MILL**](06-modules/mill.md) | Processing | Milling/machining workpieces | PICK, MILL, DROP |
| [**DRILL**](06-modules/drill.md) | Processing | Drilling operations | PICK, DRILL, DROP |
| [**OVEN**](06-modules/oven.md) | Processing | Heat treatment/baking | PICK, FIRE, DROP |
| [**AIQS**](06-modules/aiqs.md) | Quality Control | Automated quality inspection | CHECK_QUALITY, PICK, DROP |
| [**DPS**](06-modules/dps.md) | I/O | Goods receipt and delivery | PICK, DROP | DPS |
| [**HBW**](06-modules/hbw.md) | Storage | High-bay warehouse storage | PICK, DROP |
| [**AGV**](06-modules/agv.md) | Transport | Automated Guided Vehicle | DOCK, PASS, TURN |
| [**CGW**](06-modules/cgw.md) | Integration | Cloud gateway bridge | N/A (bridge only) |

### Module Categories

#### Processing Modules
Transform workpieces through physical operations:
- **MILL**: Milling/cutting operations
- **DRILL**: Drilling holes
- **OVEN**: Heat treatment

#### Support Modules
Facilitate production without transformation:
- **AIQS**: Quality inspection and routing
- **DPS**: Input/output with NFC tracking
- **HBW**: Storage and retrieval

#### Infrastructure
Enable factory operation:
- **AGV**: Transport between stations
- **CGW**: Cloud connectivity

## 6.2 Common Topics for All Modules

All production modules (MILL, DRILL, OVEN, AIQS, DPS, HBW) use the same topic structure:

### Subscribed Topics (Module receives from CCU)
```
module/v1/ff/<serial>/order          # Production commands
module/v1/ff/<serial>/instantAction  # Immediate actions
```

### Published Topics (Module sends to CCU)
```
module/v1/ff/<serial>/state          # Current state (1Hz or on change)
module/v1/ff/<serial>/connection     # ONLINE/OFFLINE status (retained + LWT)
module/v1/ff/<serial>/factsheet      # Capabilities (on startup)
```

FTS uses parallel topics with the `fts/` prefix instead of `module/`.

## 6.3 Common Commands

All production modules support these basic commands:

### PICK Command
**Purpose**: Take a workpiece from the AGV onto the module

**Example Order Message**:
```json
{
  "timestamp": "2024-12-08T10:30:00.000Z",
  "serialNumber": "MILL001",
  "orderId": "order-123",
  "orderUpdateId": 1,
  "action": {
    "id": "action-456",
    "command": "PICK"
  }
}
```

**Expected Behavior**:
1. Module activates suction/gripper
2. Picks up workpiece from AGV loading bay
3. Transports workpiece to processing position
4. Reports `FINISHED` when complete

**State Updates**:
```json
// During execution
{
  "actionState": {
    "id": "action-456",
    "state": "RUNNING",
    "command": "PICK"
  }
}

// On completion
{
  "actionState": {
    "id": "action-456",
    "state": "FINISHED",
    "command": "PICK"
  },
  "loads": [
    {
      "loadId": null,
      "loadType": "WHITE",
      "loadPosition": "MODULE"
    }
  ]
}
```

### DROP Command
**Purpose**: Place workpiece from module onto AGV

**Example Order Message**:
```json
{
  "timestamp": "2024-12-08T10:35:00.000Z",
  "serialNumber": "MILL001",
  "orderId": "order-123",
  "orderUpdateId": 3,
  "action": {
    "id": "action-789",
    "command": "DROP"
  }
}
```

**Expected Behavior**:
1. Module transports workpiece to handover position
2. Places workpiece on AGV loading bay
3. Releases workpiece
4. Returns to home position
5. Reports `FINISHED` when complete

**State Updates**:
```json
// On completion
{
  "actionState": {
    "id": "action-789",
    "state": "FINISHED",
    "command": "DROP"
  },
  "loads": []
}
```

## 6.4 Module-Specific Processing Commands

Each processing module has its unique production command:

| Module | Command | Metadata | Duration |
|--------|---------|----------|----------|
| MILL | `MILL` | `duration` (seconds) | Configurable, default 5s |
| DRILL | `DRILL` | `duration` (seconds) | Configurable, default 5s |
| OVEN | `FIRE` | `duration` (seconds) | Configurable, default 10s |
| AIQS | `CHECK_QUALITY` | None | Fixed (~3s) |

**Example MILL Command**:
```json
{
  "timestamp": "2024-12-08T10:32:00.000Z",
  "serialNumber": "MILL001",
  "orderId": "order-123",
  "orderUpdateId": 2,
  "action": {
    "id": "action-def",
    "command": "MILL",
    "metadata": {
      "duration": 8
    }
  }
}
```

## 6.5 Operating Modes

Modules can operate in different modes:

### AUTOMATIC Mode
Normal production operation. Module executes commands from the CCU.

**State Message**:
```json
{
  "operatingMode": "AUTOMATIC",
  "actionState": {...}
}
```

### TEACHIN Mode (Calibration)
Module is in calibration/setup mode. Only calibration instant actions are processed.

**State Message**:
```json
{
  "operatingMode": "TEACHIN",
  "actionState": null
}
```

**How to Enter**:
Send instant action:
```json
{
  "serialNumber": "MILL001",
  "timestamp": "2024-12-08T11:00:00.000Z",
  "actions": [
    {
      "actionType": "startCalibration",
      "actionId": "calib-123"
    }
  ]
}
```

## 6.6 Availability States

The CCU tracks module availability based on state messages:

| State | Description | Can Accept Orders? |
|-------|-------------|-------------------|
| `READY` | Idle, no active action, no errors | ✅ Yes |
| `BUSY` | Executing an action | ❌ No |
| `BLOCKED` | Error state or offline | ❌ No |

## 6.7 Error Handling

When a module encounters an error:

1. **Set Action State to FAILED**:
```json
{
  "actionState": {
    "id": "action-456",
    "state": "FAILED",
    "command": "PICK"
  }
}
```

2. **Add Error to errors Array**:
```json
{
  "errors": [
    {
      "errorType": "PICK_ERROR",
      "timestamp": "2024-12-08T10:30:15.000Z",
      "errorLevel": "FATAL",
      "errorReferences": [
        {
          "referenceKey": "reason",
          "referenceValue": "no_workpiece_detected"
        }
      ]
    }
  ]
}
```

3. **CCU Response**:
   - Marks order as `ERROR`
   - May retry or cancel depending on error type
   - Logs error for monitoring

## 6.8 Typical Action Sequence

Example: Milling a workpiece

```
1. AGV arrives and docks at MILL
   AGV publishes: {lastNodeId: "MILL001", waitingForLoadHandling: true}

2. CCU sends PICK command to MILL
   → module/v1/ff/MILL001/order {action: {command: "PICK"}}

3. MILL picks up workpiece
   MILL publishes: {actionState: {state: "RUNNING", command: "PICK"}}
   MILL publishes: {actionState: {state: "FINISHED", command: "PICK"}, loads: [{loadType: "WHITE"}]}

4. CCU sends clearLoadHandler to AGV
   → fts/v1/ff/FTS001/instantAction {actionType: "clearLoadHandler", metadata: {loadDropped: true}}

5. AGV acknowledges
   AGV publishes: {waitingForLoadHandling: false, load: []}

6. CCU sends MILL command to MILL
   → module/v1/ff/MILL001/order {action: {command: "MILL", metadata: {duration: 5}}}

7. MILL processes workpiece
   MILL publishes: {actionState: {state: "RUNNING", command: "MILL"}}
   [5 seconds pass]
   MILL publishes: {actionState: {state: "FINISHED", command: "MILL"}}

8. CCU sends DROP command to MILL
   → module/v1/ff/MILL001/order {action: {command: "DROP"}}

9. MILL returns workpiece to AGV
   MILL publishes: {actionState: {state: "RUNNING", command: "DROP"}}
   MILL publishes: {actionState: {state: "FINISHED", command: "DROP"}, loads: []}

10. CCU sends clearLoadHandler to AGV
    → fts/v1/ff/FTS001/instantAction {actionType: "clearLoadHandler", metadata: {loadDropped: false, loadType: "WHITE"}}

11. AGV acknowledges and can continue
    AGV publishes: {waitingForLoadHandling: false, load: [{loadPosition: "2", loadType: "WHITE"}]}
```

## 6.9 Module Documentation Links

For detailed command references, examples, and module-specific behavior:

- [6.2 Milling Module (MILL)](06-modules/mill.md)
- [6.3 Drilling Module (DRILL)](06-modules/drill.md)
- [6.4 Oven Module (OVEN)](06-modules/oven.md)
- [6.5 Quality Assurance (AIQS)](06-modules/aiqs.md)
- [6.6 Goods Receipt (DPS)](06-modules/dps.md)
- [6.7 High Bay Warehouse (HBW)](06-modules/hbw.md)
- [6.8 Automated Guided Vehicle (FTS)](06-modules/agv.md)
- [6.9 Cloud Gateway (CGW)](06-modules/cgw.md)

## Next Steps

- Review individual module documentation for specific examples
- See [Calibration](../07-calibration.md) for tuning production parameters
- Check [Manual Intervention](../08-manual-intervention.md) for safety guidelines
