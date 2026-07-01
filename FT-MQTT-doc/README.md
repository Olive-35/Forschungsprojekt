# MQTT Protocol Documentation - fischertechnik APS

## Overview

This documentation provides comprehensive information about the MQTT-based communication protocol used in the fischertechnik Agile Production Simulation (APS) 24V system. It is intended for developers who need to understand, integrate with, or extend the factory's MQTT interface.

### Official Resources

- [Product Page](https://www.fischertechnik.de/en/products/industry-and-universities/training-models/569289-agile-production-simulation-24v)
- [Technical Documentation](https://www.fischertechnik.de/en/industry-and-universities/technical-documents/simulate/agile-production-simulation)

## Table of Contents

1. [Introduction](01-introduction.md)
   - 1.1 Purpose of this Documentation
   - 1.2 Basic Concepts (MQTT, VDA5050, Pub/Sub)

2. [System Architecture and Overview](02-architecture.md)
   - 2.1 System Architecture
   - 2.2 Overview of Message Flows
   - 2.3 Topic Structure

3. [UI Integration and Custom Applications](03-ui-integration.md)
   - 3.1 Overview
   - 3.2 Topics Used by the Official Frontend
   - 3.3 Publishing Commands from UI
   - 3.4 Building a Custom UI
   - 3.5 Technology Stack Examples
   - 3.6 Best Practices for UI Development
   - 3.7 Security Considerations
   - 3.8 Troubleshooting
   - 3.9 Example: Complete Minimal UI

4. [Relationship with OPC-UA](04-opcua-relationship.md)
   - 4.1 Interfaces in System Context
   - 4.2 Data Exchange and Conversion

5. [Message Structure and VDA5050](05-message-structure.md)
   - 5.1 General Message Structure (Modified VDA5050)
   - 5.2 Common Header Fields
   - 5.3 Modifications to VDA5050 Standard
   - 5.4 Action States and Lifecycle

6. [Module-Specific Documentation](06-modules.md)
   - 6.1 Overview of All Modules
   - 6.2 [Milling Module (MILL)](06-modules/mill.md)
   - 6.3 [Drilling Module (DRILL)](06-modules/drill.md)
   - 6.4 [Oven Module (OVEN)](06-modules/oven.md)
   - 6.5 [Quality Control with AI (AIQS)](06-modules/aiqs.md)
   - 6.6 [Delivery and Pickup Station (DPS)](06-modules/dps.md)
   - 6.7 [High-Bay Warehouse (HBW)](06-modules/hbw.md)
   - 6.8 [Automated Guided Vehicle (AGV)](06-modules/agv.md)
   - 6.9 [Cloud Gateway (CGW)](06-modules/cgw.md)

7. [Calibration and System Actions](07-calibration.md)
   - 7.1 Calibration Overview
   - 7.2 Calibration Commands (Instant Actions)
   - 7.3 Module-Specific Calibration
   - 7.4 System Reset and Restart

8. [Manual Intervention and Best Practices](08-manual-intervention.md)
   - 8.1 Risks and Warnings
   - 8.2 Best Practices for Manual Control
   - 8.3 Common Pitfalls
   - 8.4 Debugging and Monitoring

9. [Appendices and References](09-appendices.md)
   - 9.1 VDA5050 Specification
   - 9.2 Additional Resources
   - 9.3 Glossary

10. [Tools and Testing](10-tools-and-testing.md)
    - 10.1 MQTT Analysis Tools
    - 10.2 OPC-UA Analysis Tools
    - 10.3 Docker Architecture
    - 10.4 Best Practices for Testing

11. [Scenario Examples](11-scenario-examples.md)
    - 11.1 HBW: Manual Stocking (SET_STORAGE)
    - 11.2 Triggering a Production Order
    - 11.3 System Reset
    - 11.4 AGV: Complete Navigation Flow
    - 11.5 Simulation Game
    - 11.6 HBW: Stocking via DPS

## Quick Start

For a quick overview of the system:
1. Start with the [Introduction](01-introduction.md) to understand basic concepts
2. Review the [System Architecture](02-architecture.md) for the big picture
3. Consult [Module-Specific Documentation](06-modules.md) for detailed commands and examples

## Version

This documentation corresponds to the APS 24V system.

Last updated: December 2025
