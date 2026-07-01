# 11. Scenario Examples

This chapter provides detailed JSON examples for common scenarios in the APS factory. These examples illustrate the message flow for specific operations.

## Table of Contents
- [11.1 HBW: Manual Stocking (SET_STORAGE)](#111-hbw-manual-stocking-set_storage)
- [11.2 Triggering a Production Order](#112-triggering-a-production-order)
- [11.3 System Reset](#113-system-reset)
- [11.4 AGV: Complete Navigation Flow](#114-agv-complete-navigation-flow)
- [11.5 Simulation Game](#115-simulation-game)
- [11.6 HBW: Stocking via DPS](#116-hbw-stocking-via-dps)

## 11.1 HBW: Manual Stocking (SET_STORAGE)

**Scenario**: Manually setting the inventory levels of the High-Bay Warehouse (HBW) via MQTT.

**1. Identify Device ID**
Find the Device ID of the HBW in the UI or via the `ccu/layout` topic (e.g., `HBW001` or `SVR1E94026`).

**2. Connect MQTT Client**
Connect to the broker (e.g., Host: `192.168.0.100`, Port: `1883`).

**3. Subscribe to Status Topic**
Monitor the state to verify changes:
Topic: `module/v1/ff/HBW001/state`

**4. Prepare SET_STORAGE Message**
Construct the JSON payload. You need the `workpieceId` (e.g., from NFC reader) and `type` (RED, BLUE, WHITE).

**Example: Setting specific slots**
```json
{
  "actions": [
    {
      "actionType": "SET_STORAGE",
      "actionId": "set-stock-1",
      "metadata": {
        "contents": {
          "A1": { "type": "RED",   "workpieceId": "nfcChipId1" },
          "B2": { "type": "BLUE",  "workpieceId": "nfcChipId5" },
          "C3": { "type": "WHITE", "workpieceId": "nfcChipId9" }
        }
      }
    }
  ]
}
```

**Example: Clearing the storage**
```json
{
  "actions": [
    {
      "actionType": "SET_STORAGE",
      "actionId": "clear-stock-1",
      "metadata": {
        "contents": {}
      }
    }
  ]
}
```

**5. Send Message**
Publish the JSON to the instant action topic:
Topic: `module/v1/ff/HBW001/instantAction`

**6. Verify**
Check the UI or the state topic to confirm the inventory has been updated.

## 11.2 Triggering a Production Order

**Scenario**: An external system (MES/ERP) requests the production of a BLUE workpiece.

**1. External System publishes Order**
Topic: `ccu/order/request`
```json
{
  "type": "BLUE",
  "orderType": "PRODUCTION",
  "ts": "2024-01-01T12:00:00.000Z",
  "orderId": "PROD-2024-001",
  "parameters": {
    "deadline": "2024-01-01T14:00:00.000Z"
  }
}
```

**2. CCU acknowledges Order**
Topic: `ccu/order/response`
```json
{
  "orderId": "PROD-2024-001",
  "state": "ACCEPTED",
  "ts": "2024-01-01T12:00:00.500Z"
}
```

## 11.3 System Reset

**Scenario**: An error occurred, and the operator triggers a global reset.

**1. Operator sends Reset Command**
Topic: `ccu/global`
```json
{
  "command": "reset",
  "ts": "2024-01-01T15:00:00.000Z",
  "initiator": "dashboard-user"
}
```

**2. Modules restart and clear their state**
Topic: `module/v1/ff/MILL001/state` (Example)
```json
{
  "ts": "2024-01-01T15:00:01.000Z",
  "mill": {
    "state": "READY",
    "error": false,
    "currentAction": null
  }
}
```

## 11.4 AGV: Complete Navigation Flow

**Scenario**: Initialize AGV, move between nodes, and handle docking/loading.

**Layout**: `aXYZ - 1 - 2 - 3 - abcd` (with a turn at node 3)

**1. Initialize AGV (Dock to aXYZ)**
Topic: `fts/v1/ff/ldLx/instantAction`
```json
{
   "serialNumber": "ldLx",
   "timestamp":"2022-03-03T12:12:12Z",
   "actions":[
      {
         "actionType": "findInitialDockPosition",
         "actionId": "1234567890-abcdefa",
         "metadata": {
            "nodeId": "aXYZ"
         }
      }
   ]
}
```

**2. Move aXYZ -> abcd (Drive & Dock)**
Topic: `fts/v1/ff/ldLx/order`
```json
{
   "orderId":"foo1",
   "timestamp":"2022-03-03T12:12:12Z",
   "edges":[
     { "id": "aXYZ-1", "linkedNodes": ["aXYZ", "1"], "length": 375 },
     { "id": "1-2",    "linkedNodes": ["2", "1"],    "length": 375 },
     { "id": "2-3",    "linkedNodes": ["2", "3"],    "length": 375 },
     { "id": "3-abcd", "linkedNodes": ["abcd", "3"], "length": 375 }
   ],
   "nodes":[
      { "id":"aXYZ", "linkedEdges":["aXYZ-1"] },
      { 
         "id":"1", "linkedEdges":["aXYZ-1"],
         "action":{ "type":"PASS", "metadata":{ "direction":"LEFT" }, "id":"actionId" }
      },
      { 
         "id":"2", "linkedEdges":["1-2"],
         "action":{ "type":"PASS", "id":"actionId2" }
      },
      { 
         "id":"3", "linkedEdges":["2-3", "3-abcd"],
         "action":{ "type":"TURN", "metadata": { "direction": "RIGHT" }, "id":"actionId3" }
      }, 
      {
        "id":"abcd", "linkedEdges":["3-abcd"],
         "action":{ 
            "type":"DOCK", 
            "metadata": { "loadType": "RED", "loadId": "FOO", "loadPosition": "1" },
            "id":"actionId4"
         }
      }
   ]
}
```

**3. Clear Load Handler (After Module Action)**
Topic: `fts/v1/ff/ldLx/instantAction`
```json
{
    "serialNumber": "ldLx",
    "timestamp":"2022-03-03T12:12:12Z",
    "actions":[
       {
          "actionType": "clearLoadHandler",
          "actionId": "1234567890-abcdefb",
          "metadata": { "loadType": "RED" }
       }
    ]
 }
 ```

**4. Move abcd -> aXYZ (Return Trip)**
Topic: `fts/v1/ff/ldLx/order`
```json
{
    "orderId": "foo3",
    "timestamp": "2022-03-03T12:12:12Z",
    "edges": [
      { "id": "aXYZ-1", "linkedNodes": ["aXYZ", "1"], "length": 375 },
      { "id": "1-2",    "linkedNodes": ["2", "1"],    "length": 375 },
      { "id": "2-3",    "linkedNodes": ["2", "3"],    "length": 375 },
      { "id": "3-abcd", "linkedNodes": ["abcd", "3"], "length": 375 }
    ],
    "nodes": [
      { "id": "abcd", "linkedEdges": ["3-abcd"] },
      { 
        "id": "3", "linkedEdges": ["2-3", "3-abcd"],
        "action": { "type": "TURN", "metadata": { "direction": "LEFT" }, "id": "actionId" }
      },
      { 
        "id": "2", "linkedEdges": ["2-3", "1-2"],
        "action": { "type": "PASS", "id": "actionId2" }
      },
      { 
        "id": "1", "linkedEdges": ["1-2", "aXYZ-1"],
        "action": { "type": "PASS", "id": "actionId3" }
      },
      { 
        "id": "aXYZ", "linkedEdges": ["aXYZ-1"],
        "action": { 
          "type": "DOCK", 
          "metadata": { "loadType": "RED", "loadId": "FOO", "loadPosition": "1" },
          "id": "actionId4" 
        }
      }
    ]
  }
 ```

**5. Clear Load Handler (Final)**
Topic: `fts/v1/ff/ldLx/instantAction`
```json
{
    "serialNumber": "ldLx",
    "timestamp":"2022-03-03T12:20:12Z",
    "actions":[
       {
          "actionType": "clearLoadHandler",
          "actionId": "1234567890-abcdefd",
          "metadata": { "loadType": "RED" }
       }
    ]
 }
 ```

## 11.5 Simulation Game

**Scenario**: The simulation game allows running specific production scenarios by tagging orders with a simulation ID.

> **Note**: The Simulation Game logic is primarily handled by the client (e.g., Frontend), which generates a unique `simulationId` for a session.

**Implementation Details**

1.  **Starting a Simulation**: The client generates a unique `simulationId`.
2.  **Placing Orders**: When placing orders as part of the simulation, the `simulationId` field is included in the `OrderRequest`.
    *   Topic: `ccu/order/request`
    *   Payload includes: `simulationId: "uuid-..."`
3.  **Tracking Progress**: The CCU includes the `simulationId` in the `OrderResponse` and subsequent updates. The client filters `OrderResponse` messages by this ID to track the progress of the simulation game.

**Example: Order Request with Simulation ID**

```json
{
  "type": "BLUE",
  "timestamp": "2023-10-27T10:00:00.000Z",
  "orderType": "PRODUCTION",
  "simulationId": "550e8400-e29b-41d4-a716-446655440000"
}
```
```json
{
  "ts": "2024-01-01T16:00:00.000Z",
  "level": 2,
  "score": 1500,
  "status": "RUNNING",
  "events": [
    { "type": "delivery_success", "points": 100 }
  ]
}
```

## 11.6 HBW: Stocking via DPS

**Scenario**: A workpiece is introduced at the DPS and needs to be stored in the HBW.

**1. Workpiece Introduction**
Operator places a workpiece (e.g., WHITE) at the DPS input belt.

**2. Storage Order**
An external system or the CCU triggers a storage order.
Topic: `ccu/order/request`
```json
{
  "type": "WHITE",
  "orderType": "STORAGE",
  "orderId": "STORE-001",
  "parameters": {
    "source": "DPS",
    "target": "HBW"
  }
}
```