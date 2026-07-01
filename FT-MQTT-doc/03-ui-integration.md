# 3. UI Integration and Custom Applications

## 3.1 Overview

This section describes how to build custom user interfaces or applications that interact with the APS via MQTT. The official frontend is an Angular application, but you can build clients in any language or framework that supports MQTT.

**Connection Requirements**:
- MQTT broker address (e.g., `mqtt://192.168.0.100:1883`)
- Username: `default`
- Password: `default`
- WebSocket support: Port `9001` for browser-based applications
- TCP support: Port `1883` for native applications

## 3.2 Topics Used by the Official Frontend

The official Angular frontend subscribes to the following topics to display factory state:

### 3.2.1 Device State Topics (Subscribe)

| Topic Pattern | Purpose | Retained | Update Frequency |
|--------------|---------|----------|------------------|
| `fts/v1/ff/+/state` | AGV position, battery, actions | Yes | On state change |
| `module/v1/ff/+/state` | Module actions, errors, loads | Yes | On state change |
| `fts/v1/ff/+/connection` | AGV online/offline status | Yes | On connect/disconnect |
| `module/v1/ff/+/connection` | Module online/offline status | Yes | On connect/disconnect |

**Wildcard `+`**: Matches any serial number (e.g., `FTS001`, `MILL001`)

**Usage Example**:
```javascript
// Subscribe to all AGV states
mqtt.subscribe('fts/v1/ff/+/state', (topic, message) => {
  const state = JSON.parse(message.toString());
  console.log(`AGV ${state.serialNumber}: ${state.driving ? 'driving' : 'idle'}`);
});
```

### 3.2.2 Factory State Topics (Subscribe)

| Topic | Purpose | Retained | Content Type |
|-------|---------|----------|--------------|
| `ccu/state/stock` | Current inventory | Yes | `CloudStock` |
| `ccu/state/layout` | Factory layout graph | Yes | `FactoryLayout` |
| `ccu/state/config` | System configuration | Yes | `GeneralConfig` |
| `ccu/state/flows` | Production workflows | Yes | `ProductionFlows` |
| `ccu/pairing/state` | Connected modules | Yes | `PairingState` |

**Why Retained**: These topics use retained messages so the UI displays current state immediately after connecting, without waiting for the next update.

**Usage Example**:
```javascript
// Get current stock levels
mqtt.subscribe('ccu/state/stock', (topic, message) => {
  const stock = JSON.parse(message.toString());
  console.log(`${stock.stockItems.length} items in warehouse`);
});
```

### 3.2.3 Order Management Topics (Subscribe)

| Topic | Purpose | Retained | Content Type |
|-------|---------|----------|--------------|
| `ccu/order/response` | New order created | No | `OrderResponse` |
| `ccu/order/active` | Currently running orders | Yes | `OrderResponse[]` |
| `ccu/order/completed` | Finished/cancelled orders | Yes | `OrderResponse[]` |

**Active vs Response**:
- `response`: Single order when created
- `active`: Array of all in-progress orders (updated as orders progress)
- `completed`: Array of finished orders (append-only log)

**Usage Example**:
```javascript
// Track active orders
mqtt.subscribe('ccu/order/active', (topic, message) => {
  const orders = JSON.parse(message.toString());
  orders.forEach(order => {
    console.log(`Order ${order.orderId}: ${order.state} (${order.type})`);
  });
});
```

### 3.2.4 Calibration Topics (Subscribe)

| Topic | Purpose | Retained | Content Type |
|-------|---------|----------|--------------|
| `ccu/state/calibration/+` | Live calibration data | No | `ModuleCalibrationState` |

**Usage**: Subscribe during calibration to show real-time sensor values.

## 3.3 Publishing Commands from UI

The frontend publishes to these topics to control the factory:

### 3.3.1 Order Operations (Publish)

| Topic | Purpose | QoS | Message Type |
|-------|---------|-----|--------------|
| `ccu/order/request` | Create new production order | 2 | `OrderRequest` |
| `ccu/order/cancel` | Cancel ENQUEUED orders | 2 | `string[]` (order IDs) |

**Create Order Example**:
```javascript
const orderRequest = {
  type: "WHITE",
  timestamp: new Date().toISOString(),
  orderType: "PRODUCTION"
};

mqtt.publish('ccu/order/request', JSON.stringify(orderRequest), {
  qos: 2
});
```

**Cancel Order Example**:
```javascript
// Only works for ENQUEUED orders
const orderIds = ["order-123", "order-456"];

mqtt.publish('ccu/order/cancel', JSON.stringify(orderIds), {
  qos: 2
});
```

**Important**: You cannot cancel orders once they reach `IN_PROGRESS` state. See [AGV Module Documentation](06-modules/agv.md#order-cancellation).

### 3.3.2 Configuration Changes (Publish)

| Topic | Purpose | QoS | Message Type |
|-------|---------|-----|--------------|
| `ccu/set/layout` | Update factory layout | 2 | `FactoryLayout` |
| `ccu/set/flows` | Update production workflows | 2 | `ProductionFlows` |
| `ccu/set/config` | Update system settings | 1 | `GeneralConfig` |
| `ccu/set/module-duration` | Change module timings | 2 | Module settings |
| `ccu/set/calibration` | Send calibration values | 2 | Calibration data |

**Update Layout Example**:
```javascript
const layout = {
  modules: [...],
  intersections: [...]
};

mqtt.publish('ccu/set/layout', JSON.stringify(layout), {
  qos: 2
});
```

### 3.3.3 Module Control (Publish)

| Topic | Purpose | QoS | Message Type |
|-------|---------|-----|--------------|
| `ccu/pairing/pair_fts` | Initialize AGV position | 2 | Pairing request |
| `ccu/set/charge` | Start/stop AGV charging | 2 | Charge request |
| `ccu/set/park` | Park all modules for transport | 2 | Park command |
| `ccu/set/reset` | Reset factory | 2 | Reset command |
| `ccu/set/delete-module` | Remove offline module | 2 | Serial number |

**Pair AGV Example**:
```javascript
const pairRequest = {
  ftsSerial: "FTS001",
  moduleSerial: "MILL001"
};

mqtt.publish('ccu/pairing/pair_fts', JSON.stringify(pairRequest), {
  qos: 2
});
```

## 3.4 Building a Custom UI

### 3.4.1 Minimal Read-Only Dashboard

A simple monitoring dashboard needs to subscribe to:

```javascript
const monitoringTopics = [
  'ccu/state/stock',           // Inventory
  'ccu/order/active',          // Current orders
  'ccu/pairing/state',         // Connected devices
  'fts/v1/ff/+/state',        // AGV status
  'module/v1/ff/+/state'      // Module status
];

monitoringTopics.forEach(topic => {
  mqtt.subscribe(topic, (topic, message) => {
    const data = JSON.parse(message.toString());
    updateDashboard(topic, data);
  });
});
```

**Benefits of Retained Messages**:
- Dashboard shows data immediately on page load
- No need to wait for next state update
- Works even if devices haven't sent updates recently

### 3.4.2 Full Control Application

A control application that can create orders and manage the factory:

```javascript
// 1. Subscribe to all monitoring topics (see above)

// 2. Create production order
function createOrder(workpieceType) {
  const request = {
    type: workpieceType,
    timestamp: new Date().toISOString(),
    orderType: "PRODUCTION"
  };
  
  mqtt.publish('ccu/order/request', JSON.stringify(request), {
    qos: 2
  });
}

// 3. Cancel order (only if ENQUEUED)
function cancelOrder(orderId) {
  mqtt.publish('ccu/order/cancel', JSON.stringify([orderId]), {
    qos: 2
  });
}

// 4. Update production flow
function updateFlow(flows) {
  mqtt.publish('ccu/set/flows', JSON.stringify(flows), {
    qos: 2
  });
}
```

### 3.4.3 Connection Monitoring

Track device connectivity in real-time:

```javascript
const deviceStatus = new Map();

// Subscribe to connection topics
mqtt.subscribe('fts/v1/ff/+/connection');
mqtt.subscribe('module/v1/ff/+/connection');

mqtt.on('message', (topic, message) => {
  if (topic.endsWith('/connection')) {
    const connection = JSON.parse(message.toString());
    const serialNumber = connection.serialNumber;
    
    deviceStatus.set(serialNumber, {
      online: connection.connectionState === 'ONLINE',
      lastSeen: new Date(connection.timestamp)
    });
    
    if (connection.connectionState === 'OFFLINE') {
      console.warn(`Device ${serialNumber} went offline!`);
    }
  }
});
```

### 3.4.4 Order Status Tracking

Build a complete order tracking view:

```javascript
const orders = new Map();

// Subscribe to order topics
mqtt.subscribe('ccu/order/response');  // New orders
mqtt.subscribe('ccu/order/active');    // Order updates
mqtt.subscribe('ccu/order/completed'); // Finished orders

// Subscribe to device states for detailed progress
mqtt.subscribe('fts/v1/ff/+/state');
mqtt.subscribe('module/v1/ff/+/state');

mqtt.on('message', (topic, message) => {
  const data = JSON.parse(message.toString());
  
  if (topic === 'ccu/order/response') {
    // New order created
    orders.set(data.orderId, {
      ...data,
      history: [`Order created: ${data.type}`]
    });
  }
  else if (topic === 'ccu/order/active') {
    // Bulk update of active orders
    data.forEach(order => {
      if (orders.has(order.orderId)) {
        orders.get(order.orderId).state = order.state;
        orders.get(order.orderId).productionSteps = order.productionSteps;
      }
    });
  }
  else if (topic.includes('/state')) {
    // Device state update - find matching order
    const orderId = data.orderId;
    if (orderId && orders.has(orderId)) {
      const order = orders.get(orderId);
      if (data.actionState) {
        const msg = `${data.serialNumber}: ${data.actionState.command || 'ACTION'} - ${data.actionState.state}`;
        order.history.push(msg);
      }
    }
  }
});
```

## 3.5 Technology Stack Examples

### 3.5.1 Web Browser (JavaScript)

**Library**: [MQTT.js](https://github.com/mqttjs/MQTT.js)

```javascript
const mqtt = require('mqtt');

const client = mqtt.connect('ws://192.168.0.100:9001', {
  username: 'default',
  password: 'default'
});

client.on('connect', () => {
  client.subscribe('ccu/state/stock');
  client.subscribe('ccu/order/active');
});

client.on('message', (topic, message) => {
  console.log(`Received on ${topic}:`, message.toString());
});
```

### 3.5.2 Node.js Backend

**Library**: [async-mqtt](https://github.com/mqttjs/async-mqtt)

```javascript
const mqtt = require('async-mqtt');

async function main() {
  const client = await mqtt.connectAsync('mqtt://192.168.0.100:1883', {
    username: 'default',
    password: 'default'
  });
  
  await client.subscribe('ccu/order/active');
  
  client.on('message', (topic, message) => {
    const orders = JSON.parse(message.toString());
    console.log(`${orders.length} active orders`);
  });
}
```

### 3.5.3 Python

**Library**: [paho-mqtt](https://pypi.org/project/paho-mqtt/)

```python
import paho.mqtt.client as mqtt
import json

def on_connect(client, userdata, flags, rc):
    print("Connected")
    client.subscribe("ccu/state/stock")
    client.subscribe("ccu/order/active")

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    print(f"Received on {msg.topic}: {data}")

client = mqtt.Client()
client.username_pw_set("default", "default")
client.on_connect = on_connect
client.on_message = on_message

client.connect("192.168.0.100", 1883, 60)
client.loop_forever()
```

### 3.5.4 React Application

**Library**: [react-mqtt](https://github.com/VictorHAS/react-mqtt) or MQTT.js

```jsx
import React, { useEffect, useState } from 'react';
import mqtt from 'mqtt';

function FactoryDashboard() {
  const [activeOrders, setActiveOrders] = useState([]);
  const [stock, setStock] = useState(null);
  
  useEffect(() => {
    const client = mqtt.connect('ws://192.168.0.100:9001', {
      username: 'default',
      password: 'default'
    });
    
    client.on('connect', () => {
      client.subscribe('ccu/order/active');
      client.subscribe('ccu/state/stock');
    });
    
    client.on('message', (topic, message) => {
      const data = JSON.parse(message.toString());
      
      if (topic === 'ccu/order/active') {
        setActiveOrders(data);
      } else if (topic === 'ccu/state/stock') {
        setStock(data);
      }
    });
    
    return () => client.end();
  }, []);
  
  return (
    <div>
      <h1>Factory Dashboard</h1>
      <h2>Active Orders: {activeOrders.length}</h2>
      <h2>Stock Items: {stock?.stockItems.length || 0}</h2>
    </div>
  );
}
```

## 3.6 Best Practices for UI Development

### 3.6.1 Connection Management

✅ **Do**:
- Handle reconnection automatically (most MQTT libraries do this)
- Show connection status in UI
- Buffer commands during disconnection
- Use retained messages to restore state after reconnect

❌ **Don't**:
- Assume connection is always available
- Send commands without waiting for connection
- Ignore connection state changes

### 3.6.2 Message Handling

✅ **Do**:
- Validate JSON before parsing
- Handle malformed messages gracefully
- Use TypeScript types or JSON schemas
- Parse timestamps with timezone awareness (ISO 8601)

❌ **Don't**:
- Trust message format without validation
- Assume timestamps are in local timezone
- Block UI thread with heavy processing

### 3.6.3 State Management

✅ **Do**:
- Use retained messages for initial state
- Deduplicate device states by serial number
- Track connection state separately from device state
- Buffer state updates to avoid overwhelming UI

❌ **Don't**:
- Poll for state changes (use MQTT subscriptions)
- Keep unlimited history in memory
- Update UI on every single state change (debounce)

### 3.6.4 Order Management

✅ **Do**:
- Check order state before attempting cancellation
- Track order history with device state updates
- Handle order creation responses asynchronously
- Show order state in UI (`ENQUEUED`, `IN_PROGRESS`, etc.)

❌ **Don't**:
- Attempt to cancel `IN_PROGRESS` orders (will be ignored)
- Publish orders without required fields
- Assume orders succeed immediately

### 3.6.5 QoS Selection

✅ **Do**:
- Use QoS 2 for commands (`ccu/order/request`, `ccu/set/*`)
- Use QoS 1 for subscriptions to state topics
- Let CCU control QoS for published state messages

❌ **Don't**:
- Use QoS 0 for critical commands
- Override CCU's QoS settings on subscribe

## 3.7 Security Considerations

⚠️ **Current System** (Development):
- Default credentials (`default`/`default`)
- No TLS/SSL encryption
- No authentication beyond basic username/password
- All clients have full access

🔒 **Production Recommendations**:
- Change MQTT broker credentials
- Enable TLS/SSL (`mqtts://` or `wss://`)
- Implement access control lists (ACLs) in Mosquitto
- Separate read-only and control clients
- Use client certificates for authentication
- Network isolation (VLAN, firewall rules)

## 3.8 Troubleshooting

### Connection Issues

**Problem**: Cannot connect to MQTT broker

**Solutions**:
1. Check broker is running: `mosquitto -v`
2. Verify network connectivity: `ping 192.168.0.100`
3. Test with CLI: `mosquitto_sub -h 192.168.0.100 -t '#' -u default -P default`
4. Check firewall allows ports 1883/9001

### Missing State Updates

**Problem**: UI shows old data or no data

**Solutions**:
1. Verify retained messages: `mosquitto_sub -h HOST -t 'ccu/state/stock' -u default -P default`
2. Check topic subscription uses correct wildcards (`+` not `*`)
3. Ensure JSON parsing doesn't fail silently
4. Monitor connection state - may be disconnected

### Order Not Cancelling

**Problem**: Published to `ccu/order/cancel` but order continues

**Solutions**:
1. Check order state - only `ENQUEUED` can be cancelled
2. Verify order ID is correct
3. Check QoS 2 is used for publish
4. Monitor `ccu/order/completed` for cancellation confirmation

### Performance Issues

**Problem**: UI becomes slow with many messages

**Solutions**:
1. Debounce UI updates (e.g., max 10 updates/second)
2. Limit state history buffer size
3. Unsubscribe from unused topics
4. Use `react-window` or similar for large lists
5. Move heavy processing to Web Workers

## 3.9 Example: Complete Minimal UI

Here's a complete minimal UI using vanilla JavaScript and HTML:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Factory Monitor</title>
  <script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
</head>
<body>
  <h1>Factory Monitor</h1>
  
  <div id="status">Connecting...</div>
  
  <h2>Active Orders</h2>
  <ul id="orders"></ul>
  
  <h2>Stock</h2>
  <ul id="stock"></ul>
  
  <h2>Create Order</h2>
  <button onclick="createOrder('WHITE')">White</button>
  <button onclick="createOrder('RED')">Red</button>
  <button onclick="createOrder('BLUE')">Blue</button>
  
  <script>
    const client = mqtt.connect('ws://192.168.0.100:9001', {
      username: 'default',
      password: 'default'
    });
    
    client.on('connect', () => {
      document.getElementById('status').textContent = 'Connected';
      client.subscribe('ccu/order/active');
      client.subscribe('ccu/state/stock');
    });
    
    client.on('message', (topic, message) => {
      const data = JSON.parse(message.toString());
      
      if (topic === 'ccu/order/active') {
        const list = document.getElementById('orders');
        list.innerHTML = data.map(order => 
          `<li>${order.orderId}: ${order.type} - ${order.state}</li>`
        ).join('');
      }
      else if (topic === 'ccu/state/stock') {
        const list = document.getElementById('stock');
        list.innerHTML = data.stockItems.map(item => 
          `<li>${item.location}: ${item.workpiece?.type || 'Empty'}</li>`
        ).join('');
      }
    });
    
    function createOrder(type) {
      const request = {
        type: type,
        timestamp: new Date().toISOString(),
        orderType: "PRODUCTION"
      };
      
      client.publish('ccu/order/request', JSON.stringify(request), {
        qos: 2
      });
    }
  </script>
</body>
</html>
```

Save as `monitor.html` and open in a browser. This provides:
- ✅ Live order tracking
- ✅ Stock monitoring
- ✅ Order creation
- ✅ Connection status

## 3.10 Next Steps

- Review [Message Structure](05-message-structure.md) for complete message formats
- Check [Module Documentation](06-modules.md) for device-specific commands
- See [Manual Intervention](08-manual-intervention.md) for safety warnings
- Explore [System Architecture](02-architecture.md) for deeper understanding
- Explore [System Architecture](02-architecture.md) for deeper understanding
