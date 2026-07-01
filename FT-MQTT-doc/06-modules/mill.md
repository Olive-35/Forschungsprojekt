# 6.2 Milling Station (MILL)

## Overview

The Milling Station performs milling operations on workpieces. It can pick up workpieces from the AGV, perform milling operations, and return them to the AGV.

**Module Type**: `MILL`  
**Serial Number**: Cleaned variant of the SPS serial number

## Supported Commands

| Command | Purpose | Metadata | Typical Duration |
|---------|---------|----------|------------------|
| `PICK` | Pick workpiece from AGV | None | ~3 seconds |
| `MILL` | Perform milling operation | `duration` (seconds) | Configurable (default 5s) |
| `DROP` | Return workpiece to AGV | None | ~3 seconds |

## MQTT Topics

### Subscriptions (Module listens to):
- `module/v1/ff/<serial>/order` - Production commands from CCU
- `module/v1/ff/<serial>/instantAction` - Immediate commands (calibration, reset)

### Publications (Module sends):
- `module/v1/ff/<serial>/state` - Current state (~1Hz or on change)
- `module/v1/ff/<serial>/connection` - ONLINE/OFFLINE status (retained + LWT)
- `module/v1/ff/<serial>/factsheet` - Module capabilities (on startup)

## Command Examples

### Example 1: PICK Workpiece

**Command** (CCU → Module):
```json
{
  "timestamp": "2024-12-08T10:30:00.000Z",
  "serialNumber": "MILL001",
  "orderId": "order-abc-123",
  "orderUpdateId": 1,
  "action": {
    "id": "pick-action-456",
    "command": "PICK"
  }
}
```

**State Response** (Module → CCU) during execution:
```json
{
  "headerId": 42,
  "timestamp": "2024-12-08T10:30:01.000Z",
  "serialNumber": "MILL001",
  "type": "MILL",
  "orderId": "order-abc-123",
  "orderUpdateId": 1,
  "paused": false,
  "actionState": {
    "id": "pick-action-456",
    "timestamp": "2024-12-08T10:30:01.000Z",
    "state": "RUNNING",
    "command": "PICK"
  },
  "errors": [],
  "loads": []
}
```

**State Response** on completion:
```json
{
  "headerId": 43,
  "timestamp": "2024-12-08T10:30:03.000Z",
  "serialNumber": "MILL001",
  "type": "MILL",
  "orderId": "order-abc-123",
  "orderUpdateId": 1,
  "paused": false,
  "actionState": {
    "id": "pick-action-456",
    "timestamp": "2024-12-08T10:30:03.000Z",
    "state": "FINISHED",
    "command": "PICK"
  },
  "errors": [],
  "loads": [
    {
      "loadId": null,
      "loadType": "WHITE",
      "loadPosition": "MODULE"
    }
  ]
}
```

### Example 2: MILL Operation

**Command** (CCU → Module):
```json
{
  "timestamp": "2024-12-08T10:30:05.000Z",
  "serialNumber": "MILL001",
  "orderId": "order-abc-123",
  "orderUpdateId": 2,
  "action": {
    "id": "mill-action-789",
    "command": "MILL",
    "metadata": {
      "duration": 8
    }
  }
}
```

**State Updates**:

Running state:
```json
{
  "headerId": 44,
  "timestamp": "2024-12-08T10:30:06.000Z",
  "serialNumber": "MILL001",
  "type": "MILL",
  "orderId": "order-abc-123",
  "orderUpdateId": 2,
  "paused": false,
  "actionState": {
    "id": "mill-action-789",
    "timestamp": "2024-12-08T10:30:06.000Z",
    "state": "RUNNING",
    "command": "MILL"
  },
  "errors": [],
  "loads": [
    {
      "loadType": "WHITE",
      "loadPosition": "MODULE"
    }
  ]
}
```

Finished state (after 8 seconds):
```json
{
  "headerId": 45,
  "timestamp": "2024-12-08T10:30:14.000Z",
  "serialNumber": "MILL001",
  "type": "MILL",
  "orderId": "order-abc-123",
  "orderUpdateId": 2,
  "paused": false,
  "actionState": {
    "id": "mill-action-789",
    "timestamp": "2024-12-08T10:30:14.000Z",
    "state": "FINISHED",
    "command": "MILL"
  },
  "errors": [],
  "loads": [
    {
      "loadType": "WHITE",
      "loadPosition": "MODULE"
    }
  ]
}
```

### Example 3: DROP Workpiece

**Command**:
```json
{
  "timestamp": "2024-12-08T10:30:16.000Z",
  "serialNumber": "MILL001",
  "orderId": "order-abc-123",
  "orderUpdateId": 3,
  "action": {
    "id": "drop-action-def",
    "command": "DROP"
  }
}
```

**State on Completion**:
```json
{
  "headerId": 47,
  "timestamp": "2024-12-08T10:30:19.000Z",
  "serialNumber": "MILL001",
  "type": "MILL",
  "orderId": "order-abc-123",
  "orderUpdateId": 3,
  "paused": false,
  "actionState": {
    "id": "drop-action-def",
    "timestamp": "2024-12-08T10:30:19.000Z",
    "state": "FINISHED",
    "command": "DROP"
  },
  "errors": [],
  "loads": []
}
```

## Hardware Details

### PLC Connections

The MILL module uses a Siemens S7 PLC with the following I/O:

**Inputs** (Sensors):
- Light barrier at entrance
- Light barrier at processing position
- Suction cup position sensors (inner/outer)
- Encoder signals for motor feedback

**Outputs** (Actuators):
- Conveyor belt motor (forward/reverse, PWM)
- Suction cup motors (extend/retract, PWM)
- Vacuum pump
- Compressor
- Milling motor

## Error Scenarios

### PICK_ERROR

**Cause**: No workpiece detected after PICK operation

**State Message**:
```json
{
  "actionState": {
    "id": "pick-action-456",
    "state": "FAILED",
    "command": "PICK"
  },
  "errors": [
    {
      "errorType": "PICK_ERROR",
      "timestamp": "2024-12-08T10:30:05.000Z",
      "errorLevel": "FATAL",
      "errorReferences": [
        {
          "referenceKey": "sensor",
          "referenceValue": "no_workpiece_detected"
        }
      ]
    }
  ]
}
```

### MILL_ERROR

**Cause**: Motor fault or timeout during milling

**State Message**:
```json
{
  "actionState": {
    "id": "mill-action-789",
    "state": "FAILED",
    "command": "MILL"
  },
  "errors": [
    {
      "errorType": "MILL_ERROR",
      "timestamp": "2024-12-08T10:30:10.000Z",
      "errorLevel": "FATAL",
      "errorReferences": [
        {
          "referenceKey": "reason",
          "referenceValue": "motor_fault"
        }
      ]
    }
  ]
}
```

### DROP_ERROR

**Cause**: Workpiece not released or FTS not detected

## Complete Production Cycle Example

Full sequence for milling a workpiece:

```mermaid
sequenceDiagram
    participant FTS
    participant CCU
    participant MILL

    Note over FTS: 1. FTS docks at MILL001
    CCU->>MILL: 2. PICK command
    MILL->>CCU: 3. State: RUNNING
    MILL->>CCU: 4. State: FINISHED - Load detected
    CCU->>FTS: 5. clearLoadHandler
    CCU->>MILL: 6. MILL command - duration: 8s
    MILL->>CCU: 7. State: RUNNING
    Note over MILL: 8. 8 seconds of milling
    MILL->>CCU: 9. State: FINISHED
    CCU->>MILL: 10. DROP command
    MILL->>CCU: 11. State: RUNNING
    MILL->>CCU: 12. State: FINISHED - No load
    CCU->>FTS: 13. clearLoadHandler
    Note over FTS: 14. FTS drives to next station
```

## Related Documentation

- [General Module Overview](../05-modules.md)
- [Message Structure](../04-message-structure.md)
- [Calibration](../06-calibration.md)
- [Error Handling](../07-manual-intervention.md)
