# 4. Relationship with OPC-UA

## 4.1 Interfaces in System Context

The APS uses two distinct communication protocols, each serving different purposes:

### MQTT Interface
- **Purpose**: High-level production control and coordination
- **Used By**: CCU, external systems, monitoring applications
- **Scope**: Factory-wide orchestration, order management, state monitoring
- **Protocol**: MQTT (pub/sub messaging)
- **Data Level**: Logical actions (DRILL, MILL, FIRE) and abstract states

### OPC-UA Interface
- **Purpose**: Low-level hardware control and sensor reading
- **Used By**: Node-RED bridge, PLC controllers
- **Scope**: Module-internal operations, motor control, sensor reading
- **Protocol**: OPC-UA (client-server architecture)
- **Data Level**: Physical operations (motor on/off, sensor values, position data)

### Interface Comparison

| Aspect | MQTT | OPC-UA |
|--------|------|--------|
| **Architecture** | Publish-Subscribe | Client-Server |
| **Target Users** | External integrators, CCU | Internal module control |
| **Data Format** | JSON (VDA5050-based) | Structured OPC-UA nodes |
| **Abstraction Level** | High (actions, orders) | Low (sensors, actuators) |
| **Use Case** | "Drill this workpiece" | "Turn on drill motor, move actuator" |
| **Network Scope** | Factory-wide | Module-internal |
| **Real-time** | Near real-time (~1Hz) | Real-time (PLC cycle) |

## 4.2 System Integration Architecture

```mermaid
graph TD
    External[External Systems<br/>Frontend, Custom Software] -->|MQTT High-Level Commands<br/>'Execute DRILL action'| Broker
    
    subgraph Infrastructure
        Broker[MQTT Broker<br/>Mosquitto on RPi]
        CCU[CCU<br/>Orchestration Logic]
    end
    
    Broker <-->|MQTT Subscribe/Publish| CCU
    Broker -->|MQTT Commands| NodeRED
    
    subgraph Edge_Device
        NodeRED[Node-RED Instance<br/>Protocol Translation Layer]
        
        subgraph Translation_Logic
            M2O[MQTT -> OPC-UA Translation<br/>- Receives MQTT commands<br/>- Parses VDA5050 JSON<br/>- Maps to OPC-UA node operations<br/>- Implements state machine logic]
            O2M[OPC-UA -> MQTT Translation<br/>- Polls OPC-UA nodes<br/>- Detects state changes<br/>- Generates VDA5050 state messages<br/>- Publishes to MQTT]
        end
        
        NodeRED --- M2O
        NodeRED --- O2M
    end
    
    NodeRED <-->|OPC-UA Low-Level Commands<br/>'Activate motor M1, read sensor S1'| OPCUA_Server
    
    subgraph PLC_Level
        OPCUA_Server[OPC-UA Server on PLC]
        
        subgraph Address_Space
            Nodes[Address Space:<br/>- command__PICK Boolean<br/>- command__DRILL Boolean<br/>- status__finished Boolean<br/>- status__error Boolean<br/>- calib__duration_drill Integer<br/>- ...]
        end
        
        OPCUA_Server --- Nodes
        OPCUA_Server -->|Digital I/O, Fieldbus| PLC_Logic
        
        PLC_Logic[PLC Logic Siemens S7<br/>- Motor control<br/>- Sensor reading<br/>- Safety interlocks<br/>- Position control<br/>- Timing sequences]
    end
    
    PLC_Logic -->|24V Digital I/O| Hardware
    
    subgraph Physical_Hardware
        Hardware[Physical Hardware<br/>- Motors, Actuators, Solenoids<br/>- Sensors, Light barriers, Encoders<br/>- Vacuum pumps, Compressors]
    end
```

## 4.3 Data Exchange and Conversion

### MQTT to OPC-UA Flow (Command Path)

When the CCU sends a production command via MQTT, the following conversion happens:

#### Example: DRILL Command

**1. MQTT Command (from CCU)**
```json
{
  "timestamp": "2024-12-08T10:30:00.000Z",
  "serialNumber": "DRILL001",
  "orderId": "order-123",
  "orderUpdateId": 1,
  "action": {
    "id": "action-456",
    "command": "DRILL",
    "metadata": {
      "duration": 5
    }
  }
}
```

**2. Node-RED Processing**
- Receives message on `module/v1/ff/DRILL001/order`
- Validates JSON structure
- Extracts action command: `DRILL`
- Stores orderId and actionId in internal state
- Looks up calibration parameters (duration)

**3. OPC-UA Write Operations**
Node-RED writes to PLC via OPC-UA:
```javascript
// Set command flag
write("ns=4;s=befehl__DRILL", true)

// Set duration (if configurable)
write("ns=4;s=kalib__zeit_drill", 5)
```

**4. PLC Execution**
- PLC detects `befehl__DRILL` flag
- Executes drilling sequence
  - Activate conveyor
  - Position workpiece
  - Lower drill
  - Activate drill motor
  - Wait for duration
  - Raise drill
- Sets `status__fertig` when complete

**5. OPC-UA to MQTT Flow (State Update)**

Node-RED polls OPC-UA and detects changes:
```javascript
// Periodic read
status = read("ns=4;s=status__fertig")  // returns true
error = read("ns=4;s=status__fehler")   // returns false
```

**6. MQTT State Message (to CCU)**
```json
{
  "headerId": 42,
  "timestamp": "2024-12-08T10:30:05.000Z",
  "serialNumber": "DRILL001",
  "type": "DRILL",
  "orderId": "order-123",
  "orderUpdateId": 1,
  "paused": false,
  "actionState": {
    "id": "action-456",
    "timestamp": "2024-12-08T10:30:05.000Z",
    "state": "FINISHED",
    "command": "DRILL",
    "result": "PASSED"
  },
  "errors": [],
  "loads": []
}
```

### Typical OPC-UA Node Structure

Each module exposes a set of OPC-UA nodes for control and monitoring:

#### Command Nodes (Boolean)
```
befehl__PICK          # Start PICK action
befehl__DROP          # Start DROP action
befehl__DRILL         # Start DRILL action (DRILL module)
befehl__MILL          # Start MILL action (MILL module)
befehl__FIRE          # Start FIRE action (OVEN module)
befehl__CHECK_QUALITY # Start quality check (AIQS module)
befehl__KALIBRIERE    # Enter calibration mode
befehl__ANFAHREN      # Move to position (calibration)
```

#### Status Nodes (Boolean)
```
status__fertig        # Action completed successfully
status__fehler        # Error occurred
status__bereit        # Module ready for new command
status__beschaeftigt  # Module busy
status__kalibriere_Aktiv # In calibration mode
```

#### Sensor Nodes (Boolean/Integer)
```
eingang_LS            # Light barrier at entrance
sauger_innen          # Suction cup in inner position
sauger_außen          # Suction cup in outer position
encoder_A             # Encoder signal A
encoder_B             # Encoder signal B
```

#### Calibration Parameters (Integer/Real)
```
kalib__zeit_pick      # Duration for PICK action (seconds)
kalib__zeit_drop      # Duration for DROP action (seconds)
kalib__zeit_drill     # Duration for DRILL action (seconds)
kalib__position_X     # X-axis position
kalib__position_Y     # Y-axis position
kalib__farbe_blau_richtwert  # Blue color threshold
```

## 4.4 Important Notes for Integration

### When to Use MQTT
✅ **Use MQTT for:**
- Starting production actions (DRILL, MILL, FIRE, etc.)
- Navigating FTS between modules
- Monitoring factory state
- Order management
- Configuration changes
- Error monitoring
- Integration with external systems

### When to Use OPC-UA
✅ **Use OPC-UA for:**
- Direct PLC programming (internal to module)
- Hardware-level debugging
- Custom module development
- Direct sensor value reading (if MQTT state is insufficient)
- Low-level calibration adjustments

### ⚠️ Avoid Mixing Interfaces

**Do NOT:**
- Send MQTT commands while manually controlling via OPC-UA
- Modify OPC-UA nodes directly during normal production
- Assume OPC-UA state matches MQTT state (synchronization is one-way)
- Use OPC-UA for factory-level orchestration

**Reason:** The Node-RED translation layer maintains state consistency. Manual OPC-UA changes can desynchronize the system.

### Synchronization Timing

- **MQTT → OPC-UA**: Immediate (within milliseconds)
- **OPC-UA → MQTT**: Polling-based (~100-500ms delay)
- **State Updates**: Published ~1Hz or on change
- **PLC Cycle Time**: Typically 10-100ms

### Error Propagation

Errors detected at the PLC level are propagated as follows:

```
PLC Error Detection
    ↓
status__fehler = TRUE
    ↓
Node-RED polls OPC-UA
    ↓
Node-RED detects error flag
    ↓
MQTT State Message with errors array
    ↓
CCU receives error
    ↓
Order marked as ERROR/FAILED
```

## 4.5 Which Data is Transported Where?

| Data Type | MQTT | OPC-UA |
|-----------|------|--------|
| Production Commands | ✅ Yes | ✅ Yes (via Node-RED) |
| Navigation Orders | ✅ Yes | ❌ No |
| Module State | ✅ Yes | ✅ Yes (source) |
| Sensor Values (raw) | ❌ No | ✅ Yes |
| Order Tracking | ✅ Yes | ❌ No |
| Stock Management | ✅ Yes | ❌ No |
| Error Messages | ✅ Yes | ✅ Yes (source) |
| Calibration Data | ✅ Yes | ✅ Yes |
| Factory Layout | ✅ Yes | ❌ No |
| Device Connection Status | ✅ Yes | ⚠️ Partial |
| Battery Level (FTS) | ✅ Yes | ❌ No |
| Position (encoders) | ⚠️ Abstract | ✅ Yes (raw) |

## 4.6 Node-RED as Translation Layer

Node-RED serves as the critical bridge between protocols:

### Key Responsibilities:
1. **Protocol Translation**: Converts between JSON/MQTT and OPC-UA node operations
2. **State Management**: Maintains current action state to generate proper VDA5050 messages
3. **Command Sequencing**: Ensures commands are executed in the correct order
4. **Error Detection**: Monitors OPC-UA status nodes and generates error messages
5. **Timing Control**: Implements action durations based on calibration parameters
6. **Factsheet Generation**: Publishes module capabilities on startup

### Node-RED Flow Structure (Simplified):

```
[MQTT Input] → [Parse JSON] → [Validate] → [OPC-UA Write]
                                                  ↓
[MQTT Output] ← [Format VDA5050] ← [State Machine] ← [OPC-UA Read Poll]
```

### Configuration Files
Node-RED flows are stored in:
- `nodeRed/flows.json` - Flow definitions
- `nodeRed/flows_cred.json` - Credentials (encrypted)
- `nodeRed/settings.js` - Node-RED configuration

## Next Steps

- Continue to [Message Structure](04-message-structure.md) for detailed MQTT message formats
- See [Module Documentation](06-modules.md) for specific command examples
- Review [Calibration](07-calibration.md) for OPC-UA parameter tuning
