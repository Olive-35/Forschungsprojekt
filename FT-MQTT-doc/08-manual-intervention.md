# 8. Manual Intervention and Best Practices

## 8.1 Risks and Warnings

### ⚠️ Critical Warning

**Direct MQTT manipulation during active production can cause serious system inconsistencies, deadlocks, and data corruption.**

The APS CCU maintains complex internal state based on MQTT messages. Manual intervention bypasses this state management and can lead to:

- **Factory Deadlocks**: Orders stuck indefinitely
- **Lost Workpieces**: Physical items not tracked in system
- **Phantom Workpieces**: System tracks items that don't exist
- **Module Unavailability**: Modules permanently marked as busy
- **Order Corruption**: Orders in inconsistent states
- **Data Desynchronization**: CCU state doesn't match physical reality

### When Manual Control is Dangerous

❌ **NEVER manually send messages when**:
- Production orders are active
- Modules are executing actions
- FTS are navigating
- The frontend is connected and users are working
- You don't fully understand the consequences

### What Can Go Wrong

#### Problem 1: State Consistency & Overwrites

**Scenario**: You manually publish a state message to a module's state topic.

**What Happens**:
- The module itself publishes state every ~1 second
- Your manual message is immediately overwritten
- If the module is offline, the CCU may interpret your message as the module coming online
- The CCU makes decisions based on this false state
- When the real module comes online, state conflicts occur

**Example**:
```bash
# Dangerous: Manual state message
mosquitto_pub -t "module/v1/ff/MILL001/state" -m '{"orderId":"", "actionState":null}'

# Problem: CCU thinks MILL001 is idle
# But physically: MILL001 might be busy or offline
# Result: CCU assigns new order to unavailable module → deadlock
```

#### Problem 2: UUID Mismatches

**Scenario**: You manually send an order message to a module.

**What Happens**:
- The module executes your order with your provided `actionId`
- The CCU doesn't know about this "ghost" action
- When the module reports completion, the CCU ignores it (unknown action ID)
- The module waits for the next order, but CCU thinks it's still busy
- Factory state becomes desynchronized

**Example**:
```json
// Dangerous: Manual order
{
  "orderId": "my-manual-order",
  "actionId": "my-action-123",
  "command": "DRILL"
}

// Problem: CCU doesn't track "my-manual-order"
// Module executes and reports "my-action-123" complete
// CCU: "What action? I didn't send that."
// Result: Module idle but CCU confused, tracking broken
```

#### Problem 3: Sequence ID Violations

**Scenario**: You send an order with wrong or missing `orderUpdateId`.

**What Happens**:
- VDA5050 uses sequence IDs (`orderUpdateId`, `headerId`) to detect stale messages
- Modules may reject messages with unexpected sequence numbers
- Or worse: accept them and create order history inconsistencies
- CCU's order state machine gets confused

**Example**:
```json
// Current order has orderUpdateId: 5

// Dangerous: Send update with wrong sequence
{
  "orderId": "order-123",
  "orderUpdateId": 3,  // ← WRONG! Should be 6
  "action": {...}
}

// Result: Module may reject or behave unpredictably
```

#### Problem 4: Complex Payloads

**Scenario**: You manually craft a message with incorrect or missing fields.

**What Happens**:
- JSON parsing errors
- Type validation failures
- The CCU or module crashes or logs errors
- Message is silently ignored, leaving you confused why nothing happened
- In worst case: corrupts internal state leading to undefined behavior

**Required Fields Often Missed**:
- `timestamp` (must be ISO 8601 format)
- `errors` (must be array, not missing)
- `loads` (must be array, not missing)
- Correct enum values (`State.FINISHED` vs `"FINISHED"`)

#### Problem 5: Timing & Race Conditions

**Scenario**: You send a "Job Finished" message before the CCU processes "Job Started".

**What Happens**:
- The CCU processes messages asynchronously
- Your premature "Finished" message arrives before the CCU updates its internal state
- The CCU's state machine encounters an impossible transition
- Order tracking enters undefined state
- May cause exception, crash, or silent corruption

#### Problem 6: Interfering with Planned Tasks

**Scenario**: FTS is executing navigation order from CCU. You send a different instant action.

**What Happens**:
- FTS receives your instant action while following CCU's order
- Depending on implementation:
  - FTS may cancel CCU order and execute your action (CCU left waiting)
  - FTS may queue your action (executes at wrong time)
  - FTS may ignore your action (you're confused why it didn't work)
- CCU expects FTS to arrive at destination, but it's elsewhere
- Modules waiting for FTS delivery experience timeouts
- Factory gridlock

**Example**:
```bash
# FTS is navigating: START → MILL → DRILL

# Dangerous: Manual reset
mosquitto_pub -t "fts/v1/ff/FTS001/instantAction" -m '{
  "actions": [{"actionType": "reset", "actionId": "manual-reset"}]
}'

# Result: FTS resets, forgets current order, stays at current position
# CCU still thinks FTS is navigating
# MILL module waits forever for FTS arrival
# Order stuck permanently
```

## 8.2 Safe Use Cases for Manual MQTT

### ✅ Acceptable Manual Operations

#### 1. Monitoring (Read-Only)

**Safe**: Subscribe and observe messages without publishing.

```bash
# Safe: Monitor all topics
mosquitto_sub -v -t '#'

# Safe: Monitor specific module
mosquitto_sub -v -t 'module/v1/ff/MILL001/#'

# Safe: Monitor orders
mosquitto_sub -v -t 'ccu/order/#'
```

**Use Cases**:
- Debugging message flows
- Performance monitoring
- Learning the protocol
- Creating custom dashboards

#### 2. System-Level Configuration (No Active Orders)

**Safe**: Send configuration changes when factory is idle.

**Safe Topics**:
- `ccu/set/reset` - Factory reset when idle
- `ccu/set/layout` - Update layout configuration
- `ccu/set/flows` - Update production flows
- `ccu/set/park` - Send FTS home

**Prerequisites**:
- ✅ All orders completed or cancelled
- ✅ No modules executing actions
- ✅ FTS are idle
- ✅ Frontend users notified

**Example**:
```bash
# Safe: Reset factory (only when idle!)
mosquitto_pub -t "ccu/set/reset" -m '{
  "timestamp": "2024-12-08T16:00:00.000Z",
  "resetType": "soft"
}'
```

#### 3. Order Creation (CCU Handles It)

**Safe**: Create orders through the proper request topic.

```bash
# Safe: Request new production order
mosquitto_pub -t "ccu/order/request" -m '{
  "type": "WHITE",
  "timestamp": "2024-12-08T10:00:00.000Z",
  "orderType": "PRODUCTION"
}'

# CCU handles all complexity:
# - Validates request
# - Plans production steps
# - Publishes response
# - Manages execution
```

**Why Safe**: CCU processes the request and manages all state internally.

#### 4. Order Cancellation

**Safe**: Cancel orders through the cancel topic.

```bash
# Safe: Cancel order
mosquitto_pub -t "ccu/order/cancel" -m '{
  "orderId": "order-abc-123",
  "timestamp": "2024-12-08T10:30:00.000Z"
}'
```

**CCU Actions**:
- Cancels order gracefully
- Updates order state to `CANCELLED`
- Releases reserved resources
- May allow current action to complete before cancelling

#### 5. Status LED Control (Non-Critical)

**Safe**: Control status LEDs (doesn't affect production).

```bash
# Safe: Set DPS LEDs
mosquitto_pub -t "module/v1/ff/DPS001/instantAction" -m '{
  "serialNumber": "DPS001",
  "timestamp": "2024-12-08T11:00:00.000Z",
  "actions": [{
    "actionType": "setStatusLED",
    "actionId": "led-123",
    "metadata": {"red": false, "yellow": false, "green": true}
  }]
}'
```

**Why Safe**: Passive instant action, doesn't affect availability state or production logic.

## 8.3 Best Practices for Manual Control

### Guidelines

1. **Stop Production First**
   - Cancel all active orders
   - Wait for modules to become idle
   - Park all FTS
   - Verify through monitoring before intervening

2. **Understand the State Machine**
   - Know current system state
   - Understand which message triggers which state change
   - Predict CCU's reaction to your message

3. **Use Proper JSON Format**
   - Validate JSON syntax
   - Include all required fields
   - Use correct ISO 8601 timestamps
   - Match exact enum values

4. **Generate Valid UUIDs**
   - Use UUID generators, not random strings
   - Never reuse IDs
   - Ensure uniqueness

5. **Monitor Continuously**
   - Subscribe to relevant topics while intervening
   - Watch for error messages
   - Verify expected state changes occur

6. **Test in Safe Environment**
   - Use development/test factory instance
   - Never test manual commands in production first
   - Document what works

7. **Log Everything**
   - Record manual commands sent
   - Capture system state before/after
   - Document any issues encountered

### Emergency Recovery

If manual intervention causes problems:

#### Step 1: Stop Further Damage
```bash
# Send park command
mosquitto_pub -t "ccu/set/park" -m '{"timestamp":"2024-12-08T16:00:00.000Z"}'

# Cancel all orders
mosquitto_pub -t "ccu/order/cancel" -m '{"orderId":"*","timestamp":"2024-12-08T16:00:00.000Z"}'
```

#### Step 2: Perform Factory Reset
```bash
mosquitto_pub -t "ccu/set/reset" -m '{
  "timestamp":"2024-12-08T16:05:00.000Z",
  "resetType":"soft"
}'
```

#### Step 3: Verify Physical State
- Manually check all modules for workpieces
- Note FTS positions and loads
- Clear any jammed workpieces

#### Step 4: Reinitialize FTS Positions
```bash
# For each FTS, send findInitialDockPosition
mosquitto_pub -t "fts/v1/ff/FTS001/instantAction" -m '{
  "serialNumber": "FTS001",
  "timestamp": "2024-12-08T16:10:00.000Z",
  "actions": [{
    "actionType": "findInitialDockPosition",
    "actionId": "init-1",
    "metadata": {"nodeId": "MILL001"}
  }]
}'
```

#### Step 5: Reconfigure Storage (If Needed)
```bash
# Set HBW storage contents if known
mosquitto_pub -t "module/v1/ff/HBW001/instantAction" -m '{
  "serialNumber": "HBW001",
  "timestamp": "2024-12-08T16:15:00.000Z",
  "actions": [{
    "actionType": "SET_STORAGE",
    "actionId": "set-storage-1",
    "metadata": {
      "contents": {
        "1-1": {"type": "WHITE", "workpieceId": "wp-1"},
        "2-1": {"type": "BLUE", "workpieceId": "wp-2"}
      }
    }
  }]
}'
```

## 8.4 Common Pitfalls

### Pitfall 1: "I'll just fix the state message"

❌ **Don't**: Try to "correct" a state by publishing a different state message.

✅ **Do**: Identify root cause (hardware issue, configuration problem) and fix it properly.

### Pitfall 2: "Let me test this one command quickly"

❌ **Don't**: Test in production without understanding all effects.

✅ **Do**: Use a test environment or offline system for experimentation.

### Pitfall 3: "I'll restart just the module"

❌ **Don't**: Restart/reset a single module while CCU thinks it's busy with an order.

✅ **Do**: Cancel the order in CCU first, then reset the module, then resync.

### Pitfall 4: "The message looks similar, close enough"

❌ **Don't**: Copy-paste messages with slight modifications hoping they work.

✅ **Do**: Understand every field, use proper values, validate against schema.

### Pitfall 5: "I'll just clear this error manually"

❌ **Don't**: Publish a state message with an empty errors array to "clear" errors.

✅ **Do**: Resolve the underlying problem, then let the module naturally report error-free state.

## 8.5 Debugging Guidelines

### Use MQTT Explorer or CLI Tools

**MQTT Explorer** (GUI):
- Visualize entire topic tree
- See message history
- Easy subscription management
- Good for learning

**mosquitto_sub** (CLI):
```bash
# Monitor all traffic
mosquitto_sub -h localhost -p 1883 -u default -P default -v -t '#'

# Monitor specific module
mosquitto_sub -h localhost -p 1883 -u default -P default -v -t 'module/v1/ff/MILL001/#'

# Monitor CCU state
mosquitto_sub -h localhost -p 1883 -u default -P default -v -t 'ccu/state/#'
```

### Trace Order Lifecycle

To debug an order:

1. Subscribe to order topics:
```bash
mosquitto_sub -t 'ccu/order/request' &
mosquitto_sub -t 'ccu/order/response' &
mosquitto_sub -t 'ccu/order/active' &
mosquitto_sub -t 'ccu/order/completed' &
```

2. Subscribe to relevant devices:
```bash
mosquitto_sub -t 'module/v1/ff/+/state' &
mosquitto_sub -t 'fts/v1/ff/+/state' &
```

3. Create order and watch flow through system

### Check Logs

**CCU Logs**:
```bash
# Docker environment
docker logs central-control-unit

# Look for errors
docker logs central-control-unit | grep ERROR
```

**Module Logs** (Node-RED):
- Access Node-RED UI (typically port 1880)
- Check debug nodes
- View OPC-UA connection status

## 8.6 When to Contact Support

Seek expert help when:
- Factory is in unknown state after manual intervention
- Repeated errors with no clear cause
- Physical damage suspected
- Data corruption suspected
- Unable to recover using documented procedures

**What to Provide**:
- Complete MQTT message logs during issue
- Screenshots of MQTT Explorer showing state
- CCU logs
- Description of manual commands sent
- Physical state of modules and FTS

## 8.7 Summary of Key Principles

1. **Observe, Don't Interfere**: Monitor messages without publishing during production
2. **Use Proper APIs**: Use order request/cancel topics, not direct commands
3. **Stop Before Touching**: Idle the factory before manual intervention
4. **Understand Implications**: Know how CCU will react to your message
5. **Generate Valid Data**: Proper UUIDs, timestamps, and JSON structure
6. **Have Recovery Plan**: Know how to reset and recover if things go wrong
7. **Document Actions**: Record what you did for troubleshooting
8. **Test Safely**: Use test environment for experimentation

## Next Steps

- Review [Module Documentation](06-modules.md) for proper command formats
- See [Calibration](07-calibration.md) for safe parameter tuning
- Check [Appendices](09-appendices.md) for additional resources
