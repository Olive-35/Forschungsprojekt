# 6.7 High-Bay Warehouse (HBW)

## Overview

The HBW (High-Bay Warehouse) is a storage system that stores and retrieves workpieces. It has multiple storage positions organized in a grid and uses an automated retrieval system.

**Module Type**: `HBW`  
**Serial Number**: Cleaned variant of the SPS serial number  
**Storage Capacity**: Typically 9 positions (3x3 grid)

## Supported Commands

| Command | Purpose | Metadata | Duration |
|---------|---------|----------|----------|
| `PICK` | Store workpiece from AGV into warehouse | `StoreMetadata` (type, workpieceId) | ~10-15 seconds |
| `DROP` | Retrieve workpiece from warehouse to AGV | None | ~10-15 seconds |

⚠️ **Note**: Like DPS, HBW has inverted command logic:
- `PICK` = **Store** (take from AGV, put in warehouse)
- `DROP` = **Retrieve** (take from warehouse, put on AGV)

## MQTT Topics

Standard module topics:
- Subscribe: `module/v1/ff/<serial>/order`, `module/v1/ff/<serial>/instantAction`
- Publish: `module/v1/ff/<serial>/state`, `module/v1/ff/<serial>/connection`, `module/v1/ff/<serial>/factsheet`

## Command Examples

### Example 1: PICK (Store Workpiece)

**Command**:
```json
{
  "timestamp": "2024-12-08T10:00:00.000Z",
  "serialNumber": "HBW001",
  "orderId": "order-store-123",
  "orderUpdateId": 1,
  "action": {
    "id": "pick-action-abc",
    "command": "PICK",
    "metadata": {
      "type": "BLUE",
      "workpieceId": "wp-67890"
    }
  }
}
```

**Behavior**:
1. System identifies free storage position
2. Picks workpiece from FTS
3. Transports workpiece to storage position
4. Stores workpiece in identified slot
5. Updates internal storage map

**State Response** (Finished):
```json
{
  "headerId": 25,
  "timestamp": "2024-12-08T10:00:12.000Z",
  "serialNumber": "HBW001",
  "type": "HBW",
  "orderId": "order-store-123",
  "orderUpdateId": 1,
  "paused": false,
  "actionState": {
    "id": "pick-action-abc",
    "timestamp": "2024-12-08T10:00:12.000Z",
    "state": "FINISHED",
    "command": "PICK"
  },
  "errors": [],
  "loads": [
    {
      "loadType": "BLUE",
      "loadPosition": "2-1",
      "loadId": "wp-67890"
    }
  ]
}
```

The `loadPosition` indicates storage location (e.g., "2-1" = column 2, row 1).

### Example 2: DROP (Retrieve Workpiece)

**Command**:
```json
{
  "timestamp": "2024-12-08T10:30:00.000Z",
  "serialNumber": "HBW001",
  "orderId": "order-retrieve-456",
  "orderUpdateId": 1,
  "action": {
    "id": "drop-action-def",
    "command": "DROP"
  }
}
```

⚠️ **Note**: The CCU determines which workpiece to retrieve based on order requirements and FIFO/LIFO logic.

**Behavior**:
1. System locates requested workpiece type
2. Retrieves workpiece from storage position
3. Transports to FTS interface
4. Places on FTS loading bay
5. Updates internal storage map

**State Response** (Finished):
```json
{
  "headerId": 30,
  "timestamp": "2024-12-08T10:30:14.000Z",
  "serialNumber": "HBW001",
  "type": "HBW",
  "orderId": "order-retrieve-456",
  "orderUpdateId": 1,
  "paused": false,
  "actionState": {
    "id": "drop-action-def",
    "timestamp": "2024-12-08T10:30:14.000Z",
    "state": "FINISHED",
    "command": "DROP"
  },
  "errors": [],
  "loads": []
}
```

## Storage Management

### Storage Position Naming

Storage positions follow the format: `<column>-<row>`

Example 3x3 grid:
```
1-3  2-3  3-3  (Top row)
1-2  2-2  3-2  (Middle row)
1-1  2-1  3-1  (Bottom row)
```

### Set Storage Instant Action

To manually configure storage contents (e.g., after manual intervention or system reset):

**Instant Action**:
```json
{
  "serialNumber": "HBW001",
  "timestamp": "2024-12-08T09:00:00.000Z",
  "actions": [
    {
      "actionType": "SET_STORAGE",
      "actionId": "set-storage-123",
      "metadata": {
        "contents": {
          "1-1": {
            "type": "WHITE",
            "workpieceId": "wp-111"
          },
          "2-1": {
            "type": "BLUE",
            "workpieceId": "wp-222"
          },
          "3-1": {
            "type": "RED",
            "workpieceId": "wp-333"
          }
        }
      }
    }
  ]
}
```

Empty positions can be omitted or explicitly set to `{}`.

## Hardware Details

### Physical Components

The HBW consists of:
- **X-Axis**: Horizontal movement (columns)
- **Y-Axis**: Vertical movement (rows)
- **RBG** (Regalbediengerät): Storage/retrieval unit with gripper
- **Encoders**: Position tracking for X and Y axes
- **Light Barriers**: Workpiece detection

### PLC I/O

**Inputs**:
- `ref_HRL_Y` - Y-axis reference position
- `encoder_X_A`, `encoder_X_B` - X-axis encoder
- `encoder_Y_A`, `encoder_Y_B` - Y-axis encoder
- `Lichtschranke_RBG_vorn` - Gripper front sensor
- `Lichtschranke_RBG_hinten` - Gripper rear sensor

**Outputs**:
- `xAchseZumRegal` - Move X-axis toward storage
- `xAchseZumBand` - Move X-axis toward conveyor
- `yAchseRunter` - Move Y-axis down
- `yAchseHoch` - Move Y-axis up
- `RBG_vor` - Move gripper forward
- `RBG_hinten` - Move gripper backward
- `PWM_X`, `PWM_Y`, `PWM_RBG` - PWM motor control

## Calibration

The HBW requires precise calibration of:
- **X-axis Positions**: Exact encoder values for each column
- **Y-axis Positions**: Exact encoder values for each row
- **Gripper Positions**: Extend/retract distances
- **Timing Parameters**: Movement speeds

See [Calibration Documentation](../06-calibration.md) for procedures.

## Errors

- `PICK_ERROR` - Failed to store workpiece (storage full, position error, gripper fault)
- `DROP_ERROR` - Failed to retrieve workpiece (no workpiece in requested position, gripper fault)
- Storage full errors are reported via error messages

## Storage State Tracking

The CCU tracks HBW storage state via:
- **Topic**: `ccu/state/stock`
- **Contents**: All workpieces in storage with positions

Example:
```json
{
  "ts": "2024-12-08T10:00:00.000Z",
  "stockItems": [
    {
      "workpiece": {
        "id": "wp-111",
        "type": "WHITE",
        "state": "RAW"
      },
      "location": "HBW",
      "hbw": "1-1"
    },
    {
      "workpiece": {
        "id": "wp-222",
        "type": "BLUE",
        "state": "RAW"
      },
      "location": "HBW",
      "hbw": "2-1"
    }
  ]
}
```

## Special Considerations

### Inverted Command Logic
- **PICK** = Store into warehouse (take from FTS)
- **DROP** = Retrieve from warehouse (give to FTS)

### Storage Strategy
- CCU implements FIFO (First In, First Out) by default
- Alternative strategies can be configured

### Empty Storage Handling
- System must handle "no workpiece available" scenarios
- Orders may be delayed waiting for retrieval
