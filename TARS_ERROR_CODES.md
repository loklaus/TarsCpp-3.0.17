# TARS框架错误码参考文档

## 概述

本文档详细说明了TARS框架中定义的各种错误码和消息类型常量，这些常量定义在 `servant/servant/BaseF.h` 文件中。

## 版本信息

- **TARSVERSION = 1**: TARS协议版本号
- **TUPVERSION = 3**: TUP协议版本号  
- **XMLVERSION = 4**: XML协议版本号
- **JSONVERSION = 5**: JSON协议版本号

## 调用类型

- **TARSNORMAL = 0**: 正常调用（同步调用）
- **TARSONEWAY = 1**: 单向调用（异步调用，不需要返回值）

## 错误码详解

### 成功状态码

| 错误码 | 常量名 | 描述 |
|--------|--------|------|
| 0 | TARSSERVERSUCCESS | 服务器处理成功 |

### 服务器端错误码 (-1 到 -11)

| 错误码 | 常量名 | 描述 | 可能原因 | 解决方案 |
|--------|--------|------|----------|----------|
| -1 | TARSSERVERDECODEERR | 服务器解码错误 | 客户端发送的数据格式错误或协议不匹配 | 检查客户端编码格式和协议版本 |
| -2 | TARSSERVERENCODEERR | 服务器编码错误 | 服务器无法编码响应数据 | 检查服务器端数据结构和编码逻辑 |
| -3 | TARSSERVERNOFUNCERR | 服务器无此函数错误 | 调用的函数在服务器端不存在 | 确认接口定义和函数名称正确性 |
| -4 | TARSSERVERNOSERVANTERR | 服务器无此服务错误 | 请求的服务对象不存在 | 检查服务名称和服务是否已正确部署 |
| -5 | TARSSERVERRESETGRID | 服务器重置网格错误 | 网格服务重置导致的错误 | 重新建立连接或等待服务恢复 |
| -6 | TARSSERVERQUEUETIMEOUT | 服务器队列超时错误 | 请求在服务器处理队列中等待超时 | 增加超时时间或优化服务器处理能力 |
| -7 | TARSASYNCCALLTIMEOUT | 异步调用超时错误 | 异步调用在指定时间内未完成 | 增加超时时间或检查服务器响应性能 |
| -7 | TARSINVOKETIMEOUT | 调用超时错误 | 同步调用超时（与异步调用超时使用相同错误码） | 增加超时时间或优化服务处理逻辑 |
| -8 | TARSPROXYCONNECTERR | 代理连接错误 | 无法连接到代理服务器 | 检查代理服务器状态和网络连接 |
| -9 | TARSSERVEROVERLOAD | 服务器过载错误 | 服务器负载过高，无法处理更多请求 | 扩容服务器或实施负载均衡 |
| -10 | TARSADAPTERNULL | 适配器为空错误 | 服务适配器未正确初始化 | 检查服务配置和初始化逻辑 |
| -11 | TARSINVOKEBYINVALIDESET | 无效集合调用错误 | 通过无效的服务集合调用服务 | 检查服务集合配置和路由规则 |

### 客户端错误码 (-12 到 -13)

| 错误码 | 常量名 | 描述 | 可能原因 | 解决方案 |
|--------|--------|------|----------|----------|
| -12 | TARSCLIENTDECODEERR | 客户端解码错误 | 客户端无法解析服务器响应数据 | 检查协议版本和数据格式一致性 |
| -13 | TARSSENDREQUESTERR | 发送请求错误 | 客户端发送请求到服务器失败 | 检查网络连接和服务器地址配置 |

### 通用错误码

| 错误码 | 常量名 | 描述 | 可能原因 | 解决方案 |
|--------|--------|------|----------|----------|
| -99 | TARSSERVERUNKNOWNERR | 服务器未知错误 | 未分类的服务器内部错误 | 查看服务器日志获取详细错误信息 |

## 消息类型常量

这些常量用于标识不同类型的消息，可以进行位运算组合使用：

| 值 | 常量名 | 描述 | 用途 |
|----|--------|------|------|
| 0 | TARSMESSAGETYPENULL | 空消息类型 | 默认消息类型 |
| 1 | TARSMESSAGETYPEHASH | 哈希消息类型 | 用于一致性哈希路由 |
| 2 | TARSMESSAGETYPEGRID | 网格消息类型 | 用于网格计算 |
| 4 | TARSMESSAGETYPEDYED | 染色消息类型 | 用于请求链路追踪和调试 |
| 8 | TARSMESSAGETYPESAMPLE | 采样消息类型 | 用于性能监控和采样 |
| 16 | TARSMESSAGETYPEASYNC | 异步消息类型 | 标识异步调用消息 |
| 128 | TARSMESSAGETYPESETNAME | 设置名称消息类型 | 用于设置特定的服务集合名称 |
| 256 | TARSMESSAGETYPETRACE | 追踪消息类型 | 用于分布式调用链追踪 |

## 错误处理最佳实践

### 1. 客户端错误处理
```cpp
try {
    // TARS服务调用
    int ret = proxy->someMethod();
    if (ret != TARSSERVERSUCCESS) {
        // 根据错误码进行相应处理
        switch (ret) {
            case TARSSERVERTIMEOUT:
                // 处理超时
                break;
            case TARSSERVERNOSERVANTERR:
                // 处理服务不存在
                break;
            default:
                // 处理其他错误
                break;
        }
    }
} catch (const TarsException& e) {
    // 处理TARS异常
}
```

### 2. 服务端错误处理
```cpp
int YourServantImp::someMethod(tars::TarsCurrentPtr current) {
    try {
        // 业务逻辑处理
        return TARSSERVERSUCCESS;
    } catch (const std::exception& e) {
        TLOGERROR("处理请求时发生错误: " << e.what() << endl);
        return TARSSERVERUNKNOWNERR;
    }
}
```

### 3. 超时配置建议
- **同步调用**: 根据业务复杂度设置合理的超时时间（通常3-30秒）
- **异步调用**: 可以设置较长的超时时间
- **队列超时**: 根据服务器处理能力和负载情况调整

### 4. 监控和告警
建议对以下错误码进行重点监控：
- `-6` (队列超时): 可能表示服务器负载过高
- `-7` (调用超时): 可能表示网络问题或服务性能问题  
- `-9` (服务器过载): 需要立即关注和处理
- `-8` (代理连接错误): 可能表示网络或代理服务问题

## 相关文档
- [TARS开发指南](https://tarscloud.github.io/TarsDocs/)
- [TARS协议说明](https://tarscloud.github.io/TarsDocs/base/tars-protocol.html)
- [TARS服务治理](https://tarscloud.github.io/TarsDocs/admin/)

---
*本文档基于TARS框架版本3.0.17生成*
