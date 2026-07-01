# 6.3 Drilling Station (DRILL)

## Overview

The Drilling Station performs drilling operations on workpieces. Similar to the Milling Station, it can pick up workpieces from the AGV, drill holes, and return them.

**Module Type**: `DRILL`  
**Serial Number**: Cleaned variant of the SPS serial number

## Supported Commands

| Command | Purpose | Metadata | Typical Duration |
|---------|---------|----------|------------------|
| `PICK` | Pick workpiece from AGV | None | ~3 seconds |
| `DRILL` | Perform drilling operation | `duration` (seconds) | Configurable (default 5s) |
| `DROP` | Return workpiece to AGV | None | ~3 seconds |

## MQTT Topics

Same structure as MILL module:
- Subscribe: `module/v1/ff/<serial>/order`, `module/v1/ff/<serial>/instantAction`
- Publish: `module/v1/ff/<serial>/state`, `module/v1/ff/<serial>/connection`, `module/v1/ff/<serial>/factsheet`

## Command Example: DRILL Operation

**Command**:
```json
{
  "timestamp": "2024-12-08T10:30:00.000Z",
  "serialNumber": "DRILL001",
  "orderId": "order-xyz-456",
  "orderUpdateId": 2,
  "action": {
    "id": "drill-action-123",
    "command": "DRILL",
    "metadata": {
      "duration": 6
    }
  }
}
```

**State Response** (Running):
```json
{
  "headerId": 15,
  "timestamp": "2024-12-08T10:30:01.000Z",
  "serialNumber": "DRILL001",
  "type": "DRILL",
  "orderId": "order-xyz-456",
  "orderUpdateId": 2,
  "paused": false,
  "actionState": {
    "id": "drill-action-123",
    "timestamp": "2024-12-08T10:30:01.000Z",
    "state": "RUNNING",
    "command": "DRILL"
  },
  "errors": [],
  "loads": [{"loadType": "BLUE", "loadPosition": "MODULE"}]
}
```

**State Response** (Finished):
```json
{
  "headerId": 16,
  "timestamp": "2024-12-08T10:30:07.000Z",
  "serialNumber": "DRILL001",
  "type": "DRILL",
  "orderId": "order-xyz-456",
  "orderUpdateId": 2,
  "paused": false,
  "actionState": {
    "id": "drill-action-123",
    "timestamp": "2024-12-08T10:30:07.000Z",
    "state": "FINISHED",
    "command": "DRILL"
  },
  "errors": [],
  "loads": [{"loadType": "BLUE", "loadPosition": "MODULE"}]
}
```

## Hardware Details

### PLC I/O
**Inputs**: Light barriers (entrance, processing position), suction cup sensors  
**Outputs**: Conveyor motors (PWM), suction actuators (PWM), drill motor, vacuum pump, compressor

## Errors

- `DRILL_ERROR` - Drilling motor fault or timeout
- `PICK_ERROR` - Failed to pick workpiece
- `DROP_ERROR` - Failed to drop workpiece
