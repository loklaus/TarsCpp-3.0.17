# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TarsCpp is the C++ implementation of the Tars RPC framework, a high-performance microservices framework developed by Tencent. It provides:
- RPC communication framework with multiple protocol support
- IDL (Interface Definition Language) tools for code generation
- Built-in service discovery, load balancing, and monitoring
- Support for coroutines, promises, and async programming
- Cross-platform support (Linux, macOS, Windows)

## Architecture Structure

### Core Components

**servant/** - RPC framework implementation
- `libservant/` - Core RPC library (Communicator, Servant, Proxy, Protocol)
- `protocol/` - Tars protocol definitions (.tars files)
- `promise/` - Promise-based async programming utilities
- `servant/` - Public C++ headers for framework usage

**tools/** - IDL code generation tools
- `tars2cpp/` - C++ code generator from .tars files
- `tarsgrammar/` - Tars language parser (flex/bison)
- `tarsparse/` - Tars IDL parsing library
- Multi-language support: tars2java, tars2python, tars2node, etc.

**util/** - Utility libraries
- `include/util/` - Common utilities (networking, threading, JSON, HTTP, etc.)
- Core utilities: `tc_common`, `tc_config`, `tc_http`, `tc_json`, `tc_mysql`

**examples/** - Sample applications
- `QuickStartDemo/` - Basic RPC client/server example
- `PromiseDemo/` - Async programming with promises
- `CoroutineDemo/` - Coroutine-based implementations
- `HttpDemo/` - HTTP server/client examples
- `SSLDemo/` - SSL/TLS secure communication

## Build System

### CMake Build (Primary)
```bash
# Standard build
mkdir build && cd build
cmake ..
make -j$(nproc)
make install

# Build with examples and tests
cmake -DONLY_LIB=OFF ..
make -j$(nproc)
```

### Makefile Build (Legacy)
```bash
# For individual projects using makefiles
include /usr/local/tars/cpp/makefile/makefile.tars
# Requires TARS_PATH=/usr/local/tars/cpp
```

### Build Variants
- `ONLY_LIB=ON` (default): Build only libraries
- `ONLY_LIB=OFF`: Build libraries + examples + unit tests
- `TARS_SSL=1`: Enable SSL support
- `TARS_HTTP2=1`: Enable HTTP/2 support

## Development Workflow

### 1. Service Development
1. **Define Interface**: Create `.tars` IDL file
2. **Generate Code**: Use `tars2cpp` to generate stubs
3. **Implement Service**: Create servant implementation
4. **Build Service**: Use CMake or provided makefiles

### 2. IDL Processing
```bash
# Generate C++ from .tars
tars2cpp Hello.tars

# Or use generated build target
add_custom_command(
    OUTPUT Hello.h
    COMMAND tars2cpp Hello.tars
    DEPENDS Hello.tars
)
```

### 3. Running Tests
```bash
# Build and run unit tests
cd build
make unit-test
./bin/unit-test

# Run specific test module
./bin/unit-test --gtest_filter="test_rpc.*"
```

## Key Files and Patterns

### Service Structure
- `*.tars` - Interface definition files
- `*Imp.cpp/h` - Service implementation
- `*Server.cpp/h` - Server main application
- `config.conf` - Service configuration

### Common Headers
- `servant/Application.h` - Main application framework
- `servant/Servant.h` - Base servant class
- `servant/ServantProxy.h` - Client proxy generation
- `servant/Communicator.h` - RPC communicator
- `servant/Current.h` - Request context

### Build Configuration
- `cmake/Common.cmake` - Common build settings
- `servant/makefile/makefile.tars` - Legacy makefile template
- `servant/script/cmake_tars_server.sh` - CMake project generator

## Testing

### Unit Tests
- **Location**: `unit-test/`
- **Framework**: GoogleTest
- **Build**: `make unit-test` (when ONLY_LIB=OFF)
- **Run**: `./bin/unit-test`

### Integration Tests
- **Examples**: Each demo in `examples/` has test scripts
- **Test Scripts**: `examples/*/scripts/run-*.sh`

## Environment Setup

### Dependencies
- Linux: gcc 4.1.2+, cmake 3.2+, bison 2.5+, flex 2.5+
- MySQL: 4.1.17+ (for registry service)
- Optional: OpenSSL (for SSL), nghttp2 (for HTTP/2)

### Installation Paths
- Default: `/usr/local/tars/cpp/`
- Windows: `c:/tars/cpp/`
- Include: `/usr/local/tars/cpp/include`
- Libraries: `/usr/local/tars/cpp/lib`
- Tools: `/usr/local/tars/cpp/bin/tars2cpp`

## Common Commands

### Development
```bash
# Generate service template
servant/script/create_tars_server.sh DemoServer Demo

# Build examples
cd examples/QuickStartDemo/HelloServer
mkdir build && cd build
cmake ..
make

# Run service
./HelloServer --config=config.conf
```

### Debugging
```bash
# Enable debug build
cmake -DCMAKE_BUILD_TYPE=Debug ..

# Run with valgrind
valgrind --tool=memcheck ./HelloServer --config=config.conf

# Enable verbose logging
export TARS_LOG_LEVEL=DEBUG
```