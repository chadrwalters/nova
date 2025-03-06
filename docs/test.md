# Technical Design: BACnet Integration

## 1. Introduction

This document details the technical design for integrating Degree Analytics (DA) occupancy data with Building Automation and Control Networks (BACnet) systems. The goal is to expose DA's occupancy data as virtual BACnet devices, allowing existing building management systems (BMS) to easily consume and utilize this information. The solution will be packaged as an Open Virtual Appliance (OVA) for deployment.

## 2. Goals

*   Provide DA occupancy data as BACnet objects (specifically Analog Input Objects representing occupancy counts).
*   Support BACnet/IP (as indicated by the Dockerfile using port 47808).
*   Enable discovery of virtual BACnet devices by standard BACnet clients.
*   Package the solution as a deployable OVA.
*   Provide a simple configuration mechanism for schools to map their air handlers/zones to DA zones.
*   Regularly update the virtual device values by querying the DA API.
*   Maintain a secure environment.

## 3. Non-Goals

*   Support for BACnet protocols other than BACnet/IP
*   Real-time updates
*   Complex data transformations or filtering
*   Direct integration with specific HVAC manufacturer equipment
*   Web-based or graphical interfaces
*   Running within DA's normal infrastructure (this will be an external service)
*   Complex scripting or automation in initial implementation

## 4. Architecture Overview

The system consists of two main parts:

### Cloud Components (data-api Repository)
1. **OVA Management API**
   - Endpoints for listing available OVA configurations
   - File download endpoints for OVA deployment
   - Configuration management for schools

2. **Storage**
   - S3/CloudFront for OVA file distribution
   - Configuration storage
   - API key management

### OVA Components (da_data_pipeline Repository)
1. **BACnet Server**
   - Python application using BAC0 library
   - Runs on school's network
   - Handles BACnet/IP protocol communication
   - Port 47808 exposure

2. **Data Compiler**
   - Compiles occupancy data into BACnet-compatible format
   - Updates virtual device values
   - Simple functional implementation

3. **Data Mapper**
   - Maps DA Zone IDs to BACnet Object Identifiers
   - Driven by configuration file
   - Runs within OVA

4. **Virtual BACnet Devices**
   - Representations of occupancy data as BACnet Analog Input objects
   - Dynamic "Present_Value" properties
   - Updated by Data Compiler

5. **Local Configuration**
   - School-specific settings
   - API key storage
   - Zone mappings
   - Network configuration

### 4.1 System Architecture
```mermaid
graph TB
    subgraph "DA Cloud Infrastructure"
        A[OVA Management API] --> B[Storage]
        B --> C[S3/CloudFront]
    end

    subgraph "School Network (OVA)"
        D[BACnet Server] --> E[Data Compiler]
        E --> D
        F[Data Mapper] --> D
        G[Local Config] --> D
        G --> E
        G --> F
        E --> |Poll Occupancy Data| A
    end

    subgraph "Building Systems"
        H[BMS] --> |BACnet/IP| D
    end

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style H fill:#f9f,stroke:#333,stroke-width:2px
```

### 4.2 Data Flow
```mermaid
sequenceDiagram
    participant BMS as Building Management System
    participant BS as BACnet Server
    participant DC as Data Compiler
    participant API as DA API

    BMS->>BS: Who-Is Request
    BS-->>BMS: I-Am Response

    loop Every 10 minutes
        DC->>API: GET /api/v1.0/zones
        API-->>DC: Occupancy Data
        DC->>BS: Update Present_Value
        BS-->>BMS: CoV Notification
    end

    BMS->>BS: Read Property
    BS-->>BMS: Present_Value
```

### 4.3 Deployment Process
```mermaid
graph LR
    subgraph "DA Cloud"
        A[Build OVA] --> B[Upload to S3]
        B --> C[Update API]
    end

    subgraph "School Network"
        D[Download OVA] --> E[Deploy VM]
        E --> F[Configure Network]
        F --> G[Start Services]
    end

    C --> D

    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#f9f,stroke:#333,stroke-width:2px
```

### 4.4 Network Configuration
```mermaid
graph TB
    subgraph "School Network"
        A[BACnet Server] --> B[School Network]
        B --> C[Building Management System]
        A --> D[Internet Access]
    end

    subgraph "DA Cloud"
        E[API] --> F[Internet]
        G[Storage] --> F
    end

    D --> F

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#f9f,stroke:#333,stroke-width:2px
```

## 5. Repository Structure and Responsibilities

### 5.1 data-api Repository (Cloud Components)
This repository will contain:

1. **OVA Management API**
   - Endpoints for listing available OVA configurations
   - File download endpoints for OVA deployment
   - Configuration management endpoints
   - API key management

2. **Storage Integration**
   - S3/CloudFront configuration
   - File upload/download handlers
   - Version management

3. **Configuration Management**
   - School-specific settings storage
   - Zone mapping configurations
   - API key storage and rotation

4. **Documentation**
   - API documentation
   - Deployment guides
   - Configuration guides

### 5.2 da_data_pipeline Repository (OVA Components)
This repository will contain:

1. **OVA Build Infrastructure**
   - Packer configurations for BACnet support
   - Network configuration templates
   - Security hardening scripts
   - Service deployment scripts

2. **BACnet Service**
   - Python application code
   - BACnet server implementation
   - Data compiler implementation
   - Configuration management

3. **Provisioning Scripts**
   - Network setup
   - Service installation
   - Security configuration
   - Initial setup scripts

4. **Testing Infrastructure**
   - Local development setup
   - Test configurations
   - Mock BACnet clients
   - Integration test scripts

## 6. Implementation Details

### 6.1 Cloud Implementation (data-api)
```python
# API endpoints for OVA management
def list_available_configs():
    """List available OVA configurations"""
    pass

def get_download_url(version):
    """Get S3/CloudFront URL for OVA download"""
    pass

def update_school_config(school_id, config):
    """Update school-specific configuration"""
    pass
```

### 6.2 OVA Implementation (da_data_pipeline)
```python
# Functional approach for BACnet server
def create_bacnet_server(config):
    """Create and configure BACnet server"""
    bacnet = BAC0.connect()
    return bacnet

def compile_occupancy_data(zone_data):
    """Transform occupancy data into BACnet format"""
    return transformed_data

def update_device_values(server, data):
    """Update BACnet device values"""
    pass

def setup_network(config):
    """Configure network settings"""
    pass

def start_services():
    """Start required services"""
    pass
```

### 6.3 Local Development Setup
1. **Development Environment**
   ```bash
   # Clone repositories
   git clone <data-api-repo>
   git clone <da_data_pipeline-repo>

   # Set up local Python environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Configure local network
   sudo ifconfig lo0 alias 192.168.1.100
   ```

2. **Testing Setup**
   ```bash
   # Start local BACnet server
   python bacnet_server.py

   # Run tests
   pytest tests/
   ```

### 6.4 Network Configuration
* **Cloud Requirements**
  - S3/CloudFront for OVA distribution
  - API endpoints accessible from school networks
  - Secure API key management

* **OVA Requirements**
  - Port 47808 exposed for BACnet/IP
  - Internet access for API communication
  - School network access for BMS communication

## 7. Security Considerations

1. **API Key Protection**
   - API keys stored in environment variables
   - Secure file permissions for configuration files
   - No hardcoded credentials

2. **Network Security**
   - UFW firewall rules for BACnet port
   - Network isolation where possible
   - Secure communication channels

3. **Service Security**
   - Dedicated service user
   - Minimal required permissions
   - Regular security updates

## 8. Testing Strategy

1. **Unit Tests**
   - BACnet server functionality
   - Data fetching and mapping
   - Configuration management

2. **Integration Tests**
   - BACnet protocol compliance
   - API integration
   - Configuration loading

3. **End-to-End Tests**
   - Complete system functionality
   - OVA deployment
   - Network configuration

## 9. Deployment Process

1. **OVA Build**
   ```bash
   # In da_data_pipeline repository
   cd on-prem/packer
   packer build vmware-iso-base-iso-to-vmx-packer.json
   packer build vmware-iso-base-vmx-to-ova-school-packer.json
   ```

2. **Application Deployment**
   ```bash
   # In data-api repository
   python setup.py install
   systemctl enable bacnet-server
   systemctl start bacnet-server
   ```

## 10. Monitoring and Maintenance

1. **Logging**
   - Application logs to syslog
   - BACnet protocol logs
   - Error tracking

2. **Monitoring**
   - Service health checks
   - Network connectivity
   - Data freshness

3. **Maintenance**
   - Regular updates
   - Security patches
   - Configuration backups

## 11. Next Steps

1. **Immediate Actions**
   - Set up development environment
   - Create test BACnet server
   - Implement data fetching

2. **Infrastructure Setup**
   - Create branch in da_data_pipeline
   - Add BACnet-specific configurations
   - Test OVA build process

3. **Development Process**
   - Implement core functionality
   - Add tests
   - Document code

4. **Deployment Preparation**
   - Test OVA deployment
   - Verify network configuration
   - Validate security measures
