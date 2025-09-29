# TarsCpp Backend Processing Flow Diagram

## Overview Architecture

```mermaid
graph TD
    subgraph "Client Side"
        A[Client Application] --> B[Communicator]
        B --> C[ServantProxy]
        C --> D[ObjectProxy]
        D --> E[EndpointManager]
    end

    subgraph "Network Layer"
        E --> F[Network Connection]
        F --> G[TCP/UDP/HTTP]
        G --> H[Network Connection]
    end

    subgraph "Server Side"
        H --> I[AdapterProxy]
        I --> J[Application]
        J --> K[ServantHandle]
        K --> L[ServantDispatcher]
        L --> M[Servant Implementation]
        
        subgraph "Thread Pool"
            K --> N[Worker Threads]
            N --> O[Coroutine Pool]
            O --> P[Async Processing]
        end
    end

    subgraph "Service Management"
        J --> Q[AdminServant]
        Q --> R[Registry Service]
        Q --> S[Node Management]
        Q --> T[Stat Report]
    end

    subgraph "Protocol Stack"
        C --> U[Tars Protocol]
        U --> V[Encoding/Decoding]
        V --> W[Serialization]
        W --> X[Network Buffer]
    end

    subgraph "Configuration"
        J --> Y[Config Manager]
        Y --> Z[Service Discovery]
        Y --> AA[Load Balancer]
        Y --> AB[Timeout Settings]
    end

    %% Request Flow
    A -.->|1. Request| C
    C -.->|2. Serialize| U
    U -.->|3. Network| G
    G -.->|4. Deserialize| I
    I -.->|5. Dispatch| L
    L -.->|6. Process| M
    M -.->|7. Response| L
    L -.->|8. Serialize| I
    I -.->|9. Network| G
    G -.->|10. Deserialize| C
    C -.->|11. Return| A

    style A fill:#f9f,stroke:#333
    style M fill:#9f9,stroke:#333
    style J fill:#99f,stroke:#333
    style R fill:#ff9,stroke:#333
```

## Detailed Processing Components

### 1. Client-Side Components
- **Communicator**: Central client management
- **ServantProxy**: Client-side service proxy
- **ObjectProxy**: Connection management
- **EndpointManager**: Service discovery & load balancing

### 2. Server-Side Components
- **Application**: Main server framework
- **AdapterProxy**: Network endpoint handler
- **ServantHandle**: Request dispatcher
- **Servant**: Service implementation

### 3. Concurrency Model

```mermaid
graph LR
    subgraph "Coroutine Support"
        A[Request] --> B[Coroutine Context]
        B --> C[Async Operation]
        C --> D[Yield]
        D --> E[Resume]
        E --> F[Response]
    end

    subgraph "Thread Pool"
        G[Worker Thread 1] --> H[Task Queue]
        I[Worker Thread 2] --> H
        J[Worker Thread N] --> H
        H --> K[Task Processing]
    end
```

### 4. Service Lifecycle

```mermaid
graph TD
    A[Service Start] --> B[Initialize Communicator]
    B --> C[Register with Registry]
    C --> D[Load Configuration]
    D --> E[Initialize Servants]
    E --> F[Start Network Listener]
    F --> G[Ready to Serve]
    
    H[Client Request] --> I[Locate Service]
    I --> J[Create Connection]
    J --> K[Send Request]
    K --> L[Process Request]
    L --> M[Return Response]
```

### 5. Configuration Management

```mermaid
graph LR
    A[config.conf] --> B[Config Parser]
    B --> C[Service Settings]
    B --> D[Network Settings]
    B --> E[Thread Pool Settings]
    B --> F[Protocol Settings]
    
    C --> G[Application]
    D --> H[Network Layer]
    E --> I[Thread Manager]
    F --> J[Protocol Handler]
```

## Key Processing Steps

1. **Service Registration**: Services register with registry service
2. **Client Discovery**: Clients discover services via registry
3. **Load Balancing**: Automatic load distribution
4. **Connection Pooling**: Efficient connection management
5. **Protocol Handling**: Auto serialization/deserialization
6. **Error Handling**: Built-in retry and failover
7. **Monitoring**: Real-time metrics and health checks

## Configuration Example

```ini
# Coroutine configuration
opencoroutine=1
corothreadmax=100
corothreadstack=128*1024

# Network settings
netthread=4
netthreadhandle=8

# Service discovery
registry=127.0.0.1:17890
locator=tars.tarsregistry.QueryObj@tcp -h 127.0.0.1 -p 17890
```

## Architecture Benefits

- **High Performance**: Built-in coroutine support
- **Scalability**: Horizontal scaling via service discovery
- **Reliability**: Built-in failover and retry mechanisms
- **Monitoring**: Real-time service health and metrics
- **Flexibility**: Multi-protocol support (TCP/UDP/HTTP)