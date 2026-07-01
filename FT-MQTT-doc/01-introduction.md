# 1. Introduction

## 1.1 Purpose of this Documentation

This documentation provides comprehensive information about the MQTT protocol interface of the fischertechnik Agile Production Simulation (APS) 24V system. Its primary goals are:

- **Enable Customer Independence**: Empower end customers to independently control and interact with the factory at the MQTT level
- **Facilitate Integration**: Provide all necessary information for integrating external systems with the factory
- **Support Development**: Serve as a technical reference for developers working with the factory's communication layer
- **Document Protocol Details**: Clearly explain the modified VDA5050 protocol implementation used in the system

### Target Audience

This documentation is intended for:
- Software developers integrating with the APS
- System integrators connecting external systems
- Technical personnel implementing custom control logic
- Engineers extending the factory's capabilities

## 1.2 Basic Concepts

### What is MQTT?

MQTT (Message Queuing Telemetry Transport) is a lightweight, publish-subscribe messaging protocol designed for IoT and M2M communication. Key characteristics:

- **Lightweight**: Minimal protocol overhead, ideal for resource-constrained devices
- **Publish-Subscribe Pattern**: Decouples message producers from consumers
- **Broker-Based**: A central MQTT broker manages all message routing
- **Topic-Based**: Messages are organized using hierarchical topics
- **Quality of Service (QoS)**: Supports different levels of message delivery guarantees
- **Retained Messages**: The broker can store the last message on a topic for new subscribers

### Publisher and Subscriber Pattern

The APS uses the publish-subscribe pattern extensively:

#### Publishers
- **Modules** (MILL, DRILL, OVEN, etc.): Publish their current state and status updates
- **FTS** (Automated Guided Vehicles): Publish position, battery status, and action states
- **CCU** (Central Control Unit): Publishes commands, global state, and order information

#### Subscribers
- **CCU**: Subscribes to all device states to monitor the factory
- **Modules**: Subscribe to their specific command topics
- **FTS**: Subscribes to navigation orders and instant actions
- **External Systems**: Can subscribe to any published data for monitoring

#### Topics

Topics are hierarchical strings separated by forward slashes (`/`), for example:
- `module/v1/ff/MILL001/state` - State updates from the milling module
- `fts/v1/ff/FTS001/order` - Navigation orders for a specific FTS
- `ccu/order/request` - Topic for requesting new production orders

### The VDA5050 Standard

VDA5050 is a standardized communication interface for driverless transport systems, developed by the German Association of the Automotive Industry (VDA).

#### Key Aspects of VDA5050:

- **Standardized Message Format**: Defines JSON structures for orders, states, and actions
- **Action-Based Control**: Uses discrete actions with unique IDs
- **State Reporting**: Standardized state messages with timestamps and sequence numbers
- **Error Handling**: Structured error reporting with severity levels
- **Extensibility**: Allows for custom extensions while maintaining compatibility

#### VDA5050 in the APS

The APS uses a **modified VDA5050** protocol:

- **Extended Beyond AGVs**: Originally designed for automated guided vehicles, the factory applies VDA5050 principles to all modules
- **Custom Action Types**: Includes production-specific actions (DRILL, MILL, FIRE, CHECK_QUALITY)
- **Additional Topics**: Adds CCU-specific topics for global factory control
- **Calibration Support**: Extends the protocol with calibration instant actions
- **Storage Management**: Adds workpiece tracking and storage capabilities

#### Why VDA5050?

- **Industry Standard**: Proven in industrial automation environments
- **Flexibility**: Easy to extend with custom action types
- **Interoperability**: Potential for integration with other VDA5050-compatible systems
- **Clear State Management**: Well-defined state machine for actions

### Communication Flow Overview

1. **Order Creation**: An external system or frontend sends an order request to the CCU
2. **Order Planning**: The CCU generates a production plan with individual steps
3. **Command Distribution**: The CCU sends commands to modules and FTS
4. **State Monitoring**: Devices continuously publish their state
5. **Action Execution**: Modules execute actions and report progress
6. **Order Completion**: The CCU tracks completion and updates order status

### Key Concepts Summary

| Concept | Description |
|---------|-------------|
| **MQTT Broker** | Central message router (Mosquitto) |
| **Topic** | Hierarchical address for messages |
| **Publish** | Send a message to a topic |
| **Subscribe** | Listen to messages on a topic |
| **Retained Message** | Last message stored by broker for new subscribers |
| **QoS** | Quality of Service level (0, 1, or 2) |
| **LWT** | Last Will and Testament (disconnect notification) |
| **VDA5050** | Standard protocol adapted for the factory |
| **Action** | A discrete task with unique ID and lifecycle |
| **Order** | A sequence of actions to produce a workpiece |

## Next Steps

- Continue to [System Architecture](02-architecture.md) for an overview of the factory's communication structure
- Jump to [Message Structure](05-message-structure.md) for technical details on message formats
- See [Module-Specific Documentation](06-modules.md) for detailed command examples
