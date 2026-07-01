# 6.6 Delivery and Pickup Station (DPS)

## Overview

The DPS (Delivery and Pickup Station) serves as the input/output point for the factory. It handles workpiece delivery to the factory and shipping of finished products. It includes an NFC reader/writer for workpiece tracking.

**Module Type**: `DPS`  
**Serial Number**: Cleaned variant of the SPS serial number

## Supported Commands

| Command | Purpose | Metadata | Use Case |
|---------|---------|----------|----------|
| `DROP` | Deliver raw workpiece to factory | `StoreMetadata` (type, workpieceId) | Input new workpiece |
| `PICK` | Ship finished workpiece | `DeliveryMetadata` (history) | Output completed product |

⚠️ **Note**: DPS has inverted logic compared to other modules:
- `DROP` = **Input** to factory (module "drops" a new workpiece onto AGV)
- `PICK` = **Output** from factory (module "picks" finished workpiece from AGV for delivery)

## MQTT Topics

Standard module topics:
- Subscribe: `module/v1/ff/<serial>/order`, `module/v1/ff/<serial>/instantAction`
- Publish: `module/v1/ff/<serial>/state`, `module/v1/ff/<serial>/connection`, `module/v1/ff/<serial>/factsheet`

## Command Examples

### Example 1: DROP (Input Raw Workpiece)

**Command**:
```json
{
  "timestamp": "2024-12-08T08:00:00.000Z",
  "serialNumber": "DPS001",
  "orderId": "order-input-123",
  "orderUpdateId": 1,
  "action": {
    "id": "drop-action-abc",
    "command": "DROP",
    "metadata": {
      "type": "WHITE",
      "workpieceId": "wp-12345"
    }
  }
}
```

**Behavior**:
1. Module reads NFC tag (if present)
2. Places workpiece on FTS loading bay
3. Writes workpiece metadata to NFC
4. Activates status LED (green)

**State Response** (Finished):
```json
{
  "headerId": 10,
  "timestamp": "2024-12-08T08:00:03.000Z",
  "serialNumber": "DPS001",
  "type": "DPS",
  "orderId": "order-input-123",
  "orderUpdateId": 1,
  "paused": false,
  "actionState": {
    "id": "drop-action-abc",
    "timestamp": "2024-12-08T08:00:03.000Z",
    "state": "FINISHED",
    "command": "DROP"
  },
  "errors": [],
  "loads": []
}
```

### Example 2: PICK (Output Finished Product)

**Command**:
```json
{
  "timestamp": "2024-12-08T08:30:00.000Z",
  "serialNumber": "DPS001",
  "orderId": "order-output-456",
  "orderUpdateId": 1,
  "action": {
    "id": "pick-action-def",
    "command": "PICK",
    "metadata": {
      "workpiece": {
        "workpieceId": "wp-12345",
        "type": "WHITE",
        "state": "PROCESSED",
        "history": [
          {
            "ts": 1702028400,
            "code": 100
          },
          {
            "ts": 1702028460,
            "code": 600
          },
          {
            "ts": 1702028520,
            "code": 700
          },
          {
            "ts": 1702028580,
            "code": 200
          },
          {
            "ts": 1702028640,
            "code": 800
          }
        ]
      }
    }
  }
}
```

**NFC Position Codes** (from metadata.workpiece.history):
- `100` - DPS DROP (Input)
- `200` - AIQS CHECK_QUALITY
- `300` - HBW PICK (Storage retrieval)
- `400` - HBW DROP (Storage deposit)
- `500` - OVEN FIRE
- `600` - MILL MILL
- `700` - DRILL DRILL
- `800` - DPS PICK (Output)

**Behavior**:
1. Module picks workpiece from FTS
2. Writes complete history to NFC tag
3. Outputs workpiece to delivery chute
4. Activates status LED sequence

**State Response** (Finished):
```json
{
  "headerId": 15,
  "timestamp": "2024-12-08T08:30:04.000Z",
  "serialNumber": "DPS001",
  "type": "DPS",
  "orderId": "order-output-456",
  "orderUpdateId": 1,
  "paused": false,
  "actionState": {
    "id": "pick-action-def",
    "timestamp": "2024-12-08T08:30:04.000Z",
    "state": "FINISHED",
    "command": "PICK"
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

## NFC Functionality

### NFC Tag Structure

The DPS writes JSON data to NFC tags:

```json
{
  "workpieceId": "wp-12345",
  "type": "WHITE",
  "state": "PROCESSED",
  "history": [
    {"ts": 1702028400, "code": 100},
    {"ts": 1702028460, "code": 600},
    {"ts": 1702028520, "code": 700},
    {"ts": 1702028580, "code": 200},
    {"ts": 1702028640, "code": 800}
  ]
}
```

### History Codes Mapping

See [Module Commands](../04-message-structure.md) for the complete mapping of module/command combinations to NFC position codes.

## Hardware Details

### PLC I/O
**Inputs**: Light barrier, NFC reader, camera for position detection  
**Outputs**: Conveyor motors (PWM), status LEDs (RGB), NFC writer

## Status LED Control

The DPS has RGB status LEDs that can be controlled via instant action:

**Instant Action**:
```json
{
  "serialNumber": "DPS001",
  "timestamp": "2024-12-08T09:00:00.000Z",
  "actions": [
    {
      "actionType": "setStatusLED",
      "actionId": "led-123",
      "metadata": {
        "red": false,
        "yellow": false,
        "green": true
      }
    }
  ]
}
```

## Calibration

The DPS supports calibration of:
- **Camera Position**: X/Y coordinates for different stations
- **Color Sensor**: RGB thresholds
- **Timing**: Conveyor and NFC operation timings

## Errors

- `DROP_ERROR` - Failed to deliver workpiece (NFC write error, conveyor jam)
- `PICK_ERROR` - Failed to retrieve workpiece (NFC read error, no workpiece detected)

## Special Considerations

### Command Logic
Unlike other modules where PICK takes from FTS and DROP places on FTS:
- **DPS DROP**: Places NEW workpiece onto FTS (factory input)
- **DPS PICK**: Takes FINISHED workpiece from FTS (factory output)

### NFC Tag Management
- Raw workpieces may not have NFC tags initially
- Tags are written during DROP operation
- Complete history is written during PICK operation
- NFC data enables traceability and ROBO Pro Coding integration
