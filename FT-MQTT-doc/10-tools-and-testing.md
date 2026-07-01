# 10. Tools and Testing

This chapter provides recommendations and instructions for tools used to analyze, test, and debug the MQTT and OPC-UA interfaces of the APS.

## Table of Contents
- [10.1 MQTT Analysis Tools](#101-mqtt-analysis-tools)
- [10.2 OPC-UA Analysis Tools](#102-opc-ua-analysis-tools)
- [10.3 Docker Architecture](#103-docker-architecture)
- [10.4 Best Practices for Testing](#104-best-practices-for-testing)

## 10.1 MQTT Analysis Tools

### MQTT Explorer

**MQTT Explorer** is a comprehensive and easy-to-use MQTT client that provides a structured overview of your MQTT topics. It is highly recommended for visualizing the hierarchy of topics and debugging message flows.

*   **Website**: [http://mqtt-explorer.com/](http://mqtt-explorer.com/)
*   **Purpose**: Visualizing topic tree, monitoring live messages, publishing test messages.

#### How to use with APS:

1.  **Connection**:
    *   **Host**: IP address of your MQTT broker (e.g., `localhost` or the IP of the Raspberry Pi).
    *   **Port**: `1883`
    *   **Username/Password**: `default` / `default` (standard development credentials).
2.  **Visualization**:
    *   Upon connection, you will see the topic tree on the left (e.g., `f/i/state`, `u/i/state`).
    *   Expand the nodes to see individual devices and their messages.
    *   The "Value" column shows the latest payload.
    *   The "History" graph on the right shows value changes over time.
3.  **Publishing Test Messages**:
    *   Use the "Publish" panel on the right.
    *   **Topic**: Enter the target topic (e.g., `u/i/order`).
    *   **Payload**: Select `json` and paste your test JSON.
    *   Click "Publish".

### Mosquitto CLI Tools

The `mosquitto` package includes command-line tools that are excellent for scripting and quick checks.

*   **Documentation**: [https://mosquitto.org/documentation/](https://mosquitto.org/documentation/)

#### mosquitto_sub (Subscribe)

Use this tool to listen to topics in the terminal.

**Example: Monitor all state messages**
```bash
mosquitto_sub -h localhost -t "f/i/state/#" -v
```

**Example: Monitor a specific device**
```bash
mosquitto_sub -h localhost -t "f/i/state/hbw" -v
```

#### mosquitto_pub (Publish)

Use this tool to send messages from the terminal.

**Example: Send a test order**
```bash
mosquitto_pub -h localhost -t "u/i/order" -m '{"type":"order","ts":"...","orderId":"test-1"}'
```

## 10.2 OPC-UA Analysis Tools

### UaExpert

**UaExpert** is a full-featured OPC UA Client for testing and debugging OPC UA servers.

*   **Website**: [https://www.unified-automation.com/products/development-tools/uaexpert.html](https://www.unified-automation.com/products/development-tools/uaexpert.html)
*   **Purpose**: Reading/writing raw PLC values, browsing the address space.

#### How to use with APS:

1.  **Connection**:
    *   Add a new server.
    *   Enter the endpoint URL of the PLC (e.g., `opc.tcp://192.168.0.1:4840`).
    *   Connect anonymously or with credentials if configured.
2.  **Browsing**:
    *   Navigate the "Address Space" tree on the left.
    *   Locate the variables (e.g., under `PLC1` -> `DataBlocks` -> `Global`).
3.  **Monitoring**:
    *   Drag variables to the "Data Access View" to see live values.
4.  **Control**:
    *   Double-click a value in the "Value" column to write a new value (e.g., setting `cmd__pick` to `true` for testing).

> **Note**: See [OPC-UA Relationship](04-opcua-relationship.md) for details on the variable structure.
> For a screenshot and further details, see the [Factory Documentation on OPC-UA](https://github.com/fischertechnik/Agile-Production-Simulation-24V/blob/main/OPC-UA.md).

## 10.3 Docker Architecture

The Central Control Unit (CCU) and its supporting services are typically deployed using Docker.

### Container Overview

A typical APS deployment consists of the following containers:

1.  **MQTT Broker (`eclipse-mosquitto`)**:
    *   Handles all MQTT traffic.
    *   Exposes ports `1883` (TCP) and `9001` (WebSocket).
2.  **Central Control Unit (`aps-ccu`)**:
    *   The main Node.js application containing the orchestration logic.
    *   Connects to the MQTT broker container.
3.  **Node-RED (`nodered/node-red`)**:
    *   Runs on the individual module controllers (TXT 4.0) or as a simulation bridge.
    *   Translates between MQTT and OPC-UA.
4.  **Frontend (`aps-frontend`)**:
    *   Web-based user interface for monitoring and control.
    *   Connects to the MQTT broker via WebSockets (port 9001).

> **Reference**: For detailed setup instructions and `docker-compose.yml` examples, please refer to the **README** in the main repository.

## 10.4 Best Practices for Testing

1.  **Monitor First**: Before sending commands, always open MQTT Explorer or `mosquitto_sub` to observe the current traffic.
2.  **Check QoS**: Ensure your test clients use the appropriate QoS level (usually QoS 0 or 1 for testing).
3.  **Watch for Retained Messages**: Be careful when publishing with the "Retain" flag, as this can persist invalid states.
4.  **Isolate Tests**: When testing a specific module, ensure the CCU is not trying to control it simultaneously to avoid race conditions.
