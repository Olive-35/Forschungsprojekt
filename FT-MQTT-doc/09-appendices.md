# 9. Appendices and References

## Table of Contents
- [9.1 VDA5050 Specification](#91-vda5050-specification)
- [9.2 Additional Resources](#92-additional-resources)
- [9.3 Glossary](#93-glossary)
- [9.4 Quick Reference Cards](#94-quick-reference-cards)
- [9.5 Troubleshooting Index](#95-troubleshooting-index)
- [9.6 Document Version History](#96-document-version-history)
- [9.7 Contact and Support](#97-contact-and-support)

## 9.1 VDA5050 Specification

### Official VDA5050 Resources

- **Official Website**: [VDA 5050](https://www.vda.de/en/services/Publications/vda-5050-v-2-0-1.html)
- **GitHub Repository**: [VDA5050 on GitHub](https://github.com/VDA5050/VDA5050)
- **Protocol Version Used**: Modified VDA 5050 (based on v2.0)

### Key Differences in APS Implementation

The APS uses a modified version of VDA5050:

| Aspect | Standard VDA5050 | APS Implementation |
|--------|------------------|------------------------------|
| **Target Devices** | AGVs only | All modules + AGVs |
| **Action Types** | AGV-specific | Production actions added (DRILL, MILL, FIRE, etc.) |
| **Topics** | AGV control | Extended with CCU, calibration, and storage topics |
| **Instant Actions** | Limited set | Extended with calibration and system actions |
| **Workpiece Tracking** | Not specified | Full lifecycle tracking with NFC |
| **Storage Management** | Not covered | HBW storage with position tracking |

### VDA5050 Core Concepts Applied

Despite modifications, the factory maintains VDA5050 core principles:
- **Action-based control** with unique IDs
- **State machine** for action lifecycle
- **Structured error reporting**
- **Sequence numbering** for message ordering
- **JSON message format**
- **MQTT transport protocol**

## 9.2 Additional Resources

### Internal Documentation

**Source Code Documentation**:
- Protocol definitions: `common/protocol/*.ts`
- CCU implementation: `central-control/src/`
- Module specifications: `doc-source/*.md`

**GitLab Repositories**:
- Central Control Unit: This repository
- Individual Modules: Separate repositories (see module README files)
- Node-RED Flows: `nodeRed/` directory

### fischertechnik Resources

- **fischertechnik Official**: [www.fischertechnik.de](https://www.fischertechnik.de)
- **TXT 4.0 Controller**: Documentation for the controller platform
- **ROBO Pro Coding**: Programming environment for modules
- **fischertechnik Cloud**: Cloud platform documentation

### MQTT Resources

- **MQTT.org**: [https://mqtt.org/](https://mqtt.org/)
- **MQTT 3.1.1 Spec**: [OASIS Standard](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html)
- **Mosquitto Broker**: [https://mosquitto.org/](https://mosquitto.org/)
- **MQTT Explorer**: [http://mqtt-explorer.com/](http://mqtt-explorer.com/)

### OPC-UA Resources

- **OPC Foundation**: [https://opcfoundation.org/](https://opcfoundation.org/)
- **OPC UA Specification**: [OPC UA Part 1-14](https://reference.opcfoundation.org/)
- **Node-RED OPC-UA**: [node-red-contrib-opcua](https://flows.nodered.org/node/node-red-contrib-opcua)

### Development Tools

**MQTT Clients**:
- **MQTT Explorer** (GUI): Cross-platform, visual topic browser
- **mosquitto_pub/sub** (CLI): Command-line tools
- **MQTTX** (GUI): Modern client with scripting
- **Paho MQTT** (Libraries): Python, JavaScript, Java clients

**JSON Tools**:
- **jq**: Command-line JSON processor
- **JSONLint**: JSON validator
- **Postman**: API testing (supports MQTT)

**Monitoring**:
- **Node-RED Dashboard**: Real-time visualization
- **Grafana**: Time-series monitoring
- **Docker logs**: Container log analysis

## 9.3 Glossary

### Terms

| Term | Description |
|------|-------------|
| **Action** | A discrete task with unique ID that goes through a state lifecycle (WAITING → RUNNING → FINISHED/FAILED) |
| **Action ID** | Unique identifier for a specific action instance |
| **Action State** | Current status of an action (state, timestamp, result) |
| **AGV** | Automated Guided Vehicle |
| **AIQS** | Automated Inspection Quality System - quality control module |
| **Availability State** | Module's readiness to accept new orders (READY, BUSY, BLOCKED) |
| **Bay** | Loading position on AGV (1, 2, or 3) |
| **CCU** | Central Control Unit - orchestrates entire factory |
| **CGW** | Cloud Gateway - bridges local MQTT to cloud |
| **Calibration** | Process of adjusting module parameters for optimal performance |
| **Connection State** | Online/offline status of a device |
| **DPS** | Delivery and Pickup Station - input/output module with NFC |
| **Edge** | Path segment between two nodes in AGV navigation |
| **Factsheet** | Static device capability information published on startup |
| **FTS** | Topic prefix for AGV |
| **HBW** | Hochregallager (High Bay Warehouse) - storage module |
| **headerId** | Incrementing sequence number for messages from a device |
| **Instant Action** | Immediate command that can interrupt or override normal operation |
| **Last Will and Testament (LWT)** | MQTT feature for automatic disconnect notification |
| **Load** | Workpiece currently on a device |
| **Module** | Production station (MILL, DRILL, OVEN, etc.) or support module (DPS, HBW, AIQS) |
| **Module Type** | Classification of module (enum: MILL, DRILL, OVEN, AIQS, DPS, HBW, START, CHRG) |
| **MQTT** | Message Queuing Telemetry Transport - lightweight pub/sub protocol |
| **NFC** | Near Field Communication - used for workpiece tracking |
| **NiO** | Not in Order - reject output for failed quality checks |
| **Node** | Destination point in AGV navigation (typically a module serial number) |
| **OPC-UA** | OPC Unified Architecture - industrial communication protocol |
| **Order** | Production request with series of steps to complete |
| **Order ID** | Unique identifier for a production order |
| **orderUpdateId** | Sequence number for updates to a specific order |
| **PLC** | Programmable Logic Controller (Siemens S7 in this system) |
| **QoS** | Quality of Service - MQTT message delivery guarantee level |
| **Retained Message** | MQTT message stored by broker and sent to new subscribers |
| **Serial Number** | Unique identifier for a device (e.g., MILL001, AGV001) |
| **State** | Current status of an action (WAITING, INITIALIZING, RUNNING, PAUSED, FINISHED, FAILED) |
| **Topic** | Hierarchical address for MQTT messages (e.g., ccu/order/request) |
| **UUID** | Universally Unique Identifier - ensures unique IDs across system |
| **VDA5050** | Communication standard for AGVs, adapted for entire factory |
| **Workpiece** | Item being manufactured (WHITE, BLUE, or RED) |
| **Workpiece ID** | Unique identifier for tracking individual workpieces |

### Acronyms

| Acronym | Full Form |
|---------|-----------|
| AGV | Automated Guided Vehicle |
| AIQS | Automated Inspection Quality System |
| CCU | Central Control Unit |
| CGW | Cloud Gateway |
| DPS | Delivery and Pickup Station |
| FTS | Topic prefix for AGV |
| HBW | Hochregallager (High Bay Warehouse) |
| I/O | Input/Output |
| IoT | Internet of Things |
| JSON | JavaScript Object Notation |
| LWT | Last Will and Testament |
| M2M | Machine to Machine |
| MQTT | Message Queuing Telemetry Transport |
| NFC | Near Field Communication |
| NiO | Not in Order |
| OPC-UA | OPC Unified Architecture |
| PLC | Programmable Logic Controller |
| PWM | Pulse Width Modulation |
| QoS | Quality of Service |
| ROBO | Robot/Robotics (fischertechnik programming environment) |
| TLS | Transport Layer Security |
| TXT | fischertechnik controller model |
| UUID | Universally Unique Identifier |
| VDA | Verband der Automobilindustrie (German Association of the Automotive Industry) |

### Module Type Codes

| Code | Module Name | Function |
|------|-------------|----------|
| MILL | Milling Module | Milling/machining operations |
| DRILL | Drilling Module | Drilling operations |
| OVEN | Oven Module | Heat treatment/baking |
| AIQS | Quality Assurance | Automated quality inspection |
| DPS | Delivery/Pickup Station | Input/output with NFC tracking |
| HBW | High Bay Warehouse | Storage and retrieval |
| AGV | Transport Vehicle | Automated guided vehicle |
| CGW | Cloud Gateway | Cloud connectivity |
| START | Start Position | Placeholder for order generation |
| CHRG | Charging Station | AGV battery charging |

### Command Types

**Module Commands** (ModuleCommandType):
| Command | Used By | Description |
|---------|---------|-------------|
| DRILL | DRILL | Perform drilling operation |
| MILL | MILL | Perform milling operation |
| FIRE | OVEN | Perform heating operation |
| CHECK_QUALITY | AIQS | Perform quality inspection |
| PICK | All modules | Pick workpiece from AGV (or store in HBW) |
| DROP | All modules | Drop workpiece to AGV (or retrieve from HBW) |

**AGV Commands** (FtsCommandType):
| Command | Description |
|---------|-------------|
| DOCK | Dock at module for load exchange |
| PASS | Drive past node without stopping |
| TURN | Change direction at intersection |

**Instant Actions** (Selection):
| Action | Purpose |
|--------|---------|
| startCalibration | Enter calibration mode |
| stopCalibration | Exit calibration mode |
| setCalibrationValues | Update calibration parameters |
| reset | Reset device |
| clearLoadHandler | Confirm AGV load handling complete |
| findInitialDockPosition | Initialize AGV position |
| SET_STORAGE | Set HBW storage contents |
| setStatusLED | Control status LEDs |
| factsheetRequest | Request device capabilities |

### State Values

**Action States**:
- WAITING - Created but not started
- INITIALIZING - Preparing to execute
- RUNNING - Currently executing
- PAUSED - Temporarily stopped
- FINISHED - Completed successfully
- FAILED - Error occurred

**Availability States**:
- READY - Idle and available
- BUSY - Executing an action
- BLOCKED - Unavailable (error or offline)

**Order States**:
- ENQUEUED - Created and waiting
- IN_PROGRESS - Currently executing
- FINISHED - Completed successfully
- CANCELLED - User cancelled
- ERROR - Failed due to error

**Connection States**:
- ONLINE - Connected
- OFFLINE - Disconnected
- CONNECTIONBROKEN - Connection lost

## 9.4 Quick Reference Cards

### MQTT Topic Cheat Sheet

**CCU Topics**:
```
ccu/global                  - Global commands
ccu/order/request           - Create order (subscribe)
ccu/order/response          - Order confirmation (publish)
ccu/order/active            - Active orders (publish, retained)
ccu/order/completed         - Finished orders (publish, retained)
ccu/order/cancel            - Cancel order (subscribe)
ccu/state/stock             - Current inventory (publish, retained)
ccu/state/layout            - Factory layout (publish, retained)
ccu/set/reset               - Factory reset (subscribe)
ccu/set/park                - Park all AGV (subscribe)
```

**Module Topics** (replace `<serial>` with actual serial like MILL001):
```
module/v1/ff/<serial>/state          - State updates (publish, 1Hz)
module/v1/ff/<serial>/order          - Commands (subscribe)
module/v1/ff/<serial>/instantAction  - Instant actions (subscribe)
module/v1/ff/<serial>/connection     - Online/offline (publish, retained, LWT)
module/v1/ff/<serial>/factsheet      - Capabilities (publish, on startup)
```

**AGV Topics** (same structure as modules but `fts/` prefix):
```
fts/v1/ff/<serial>/state          
fts/v1/ff/<serial>/order          
fts/v1/ff/<serial>/instantAction  
fts/v1/ff/<serial>/connection     
fts/v1/ff/<serial>/factsheet      
```

### Command Quick Reference

**Create Order**:
```json
Topic: ccu/order/request
{"type": "WHITE", "timestamp": "2024-12-08T10:00:00.000Z", "orderType": "PRODUCTION"}
```

**Send Module Command**:
```json
Topic: module/v1/ff/MILL001/order
{"timestamp": "...", "serialNumber": "MILL001", "orderId": "...", "orderUpdateId": 1,
 "action": {"id": "...", "command": "MILL", "metadata": {"duration": 5}}}
```

**Cancel Order**:
```json
Topic: ccu/order/cancel
{"orderId": "order-123", "timestamp": "2024-12-08T10:30:00.000Z"}
```

**Factory Reset**:
```json
Topic: ccu/set/reset
{"timestamp": "2024-12-08T16:00:00.000Z", "resetType": "soft"}
```

## 9.5 Troubleshooting Index

**Problem**: Order stuck in IN_PROGRESS  
**Solutions**: Check module/AGV states, verify no errors, check for UUID mismatches

**Problem**: Module not accepting commands  
**Solutions**: Verify module is READY (not BUSY/BLOCKED), check connection state, verify orderUpdateId

**Problem**: AGV not moving  
**Solutions**: Check waitingForLoadHandling flag, verify navigation order sent, check for errors

**Problem**: Workpiece not tracked correctly  
**Solutions**: Verify clearLoadHandler sent, check load arrays in state messages, verify NFC operation

**Problem**: Calibration changes not persisting  
**Solutions**: Send storeCalibrationValues instant action, verify acknowledgment

**Problem**: Can't enter calibration mode  
**Solutions**: Cancel active orders first, verify module is idle, check for errors

## 9.6 Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | December 2025 | Initial comprehensive documentation |

## 9.7 Contact and Support

For questions, issues, or contributions related to this documentation:

- **Source Code**: Internal GitLab repository
- **Module Documentation**: See individual module repositories
- **Protocol Definitions**: `common/protocol/` directory

---

**End of Documentation**

For the latest updates and additional resources, refer to the project README and source code documentation.
