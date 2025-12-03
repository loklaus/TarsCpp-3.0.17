# TarsCpp 配置使用完全指南

## 概述

本指南详细说明如何在TarsCpp框架中配置和使用各种线程、协程及性能相关参数，帮助开发者根据业务场景优化服务性能。

## 配置文件结构

### 标准配置文件格式

所有TarsCpp服务的配置文件采用XML格式，位于服务目录下的 `config.conf` 文件中：

```xml
<tars>
  <application>
    <client>
      <!-- 客户端配置 -->
    </client>
    <server>
      <!-- 服务端配置 -->
      <AdapterName>
        <!-- 适配器配置 -->
      </AdapterName>
    </server>
  </application>
</tars>
```

## 完整配置参数列表

### Client 配置参数

所有客户端配置位于 `/tars/application/client` 路径下：

#### 基础连接配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `locator` | string | - | 主控定位器地址，格式：`tars.tarsregistry.QueryObj@tcp -h IP -p PORT` |
| `modulename` | string | - | 模块名称，用于统计上报 |
| `sync-invoke-timeout` | int | 3000 | 同步调用超时时间（毫秒） |
| `async-invoke-timeout` | int | 5000 | 异步调用超时时间（毫秒） |
| `connect-timeout` | int | 1500 | 连接超时时间（毫秒） |
| `refresh-endpoint-interval` | int | 10000 | 刷新端点列表间隔（毫秒） |

#### 线程配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `netthread` | int | 1 | 客户端网络IO线程数 |
| `asyncthread` | int | 3 | 异步回调处理线程数 |
| `mergenetasync` | int | 0 | 是否合并网络和同步线程（0/1） |

#### 队列配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `sendqueuelimit` | int | 100000 | 发送队列最大长度 |
| `asyncqueuecap` | int | 100000 | 异步队列容量 |

#### 统计上报配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `stat` | string | - | 统计服务对象名，格式：`tars.tarsstat.StatObj` |
| `property` | string | - | 属性上报服务对象名，格式：`tars.tarsproperty.PropertyObj` |
| `report-interval` | int | 60000 | 统计上报间隔（毫秒） |
| `keep-alive-interval` | int | 0 | Keepalive心跳间隔（毫秒），0表示不启用 |

#### SET部署配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enableset` | string | N | 是否启用SET部署（Y/N） |
| `setdivision` | string | - | SET分组信息，格式：`set名.地区.组名`，如：`gray.sz.1` |

#### SSL/TLS配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ca` | string | - | CA证书文件路径 |
| `cert` | string | - | 客户端证书文件路径 |
| `key` | string | - | 客户端私钥文件路径 |
| `ciphers` | string | - | SSL密码套件，如：`ECDHE-RSA-AES256-GCM-SHA384` |

#### 特定服务对象配置

可在 `<client>` 下为特定服务对象配置独立的参数：

```xml
<client>
    <服务对象名>
        ca=证书路径
        cert=客户端证书路径
        key=私钥路径
        accesskey=访问密钥
        secretkey=密钥
        ciphers=密码套件
    </服务对象名>
</client>
```

**示例**：
```xml
<client>
    <TestApp.HelloServer.HelloObj>
        ca=/path/to/ca.crt
        cert=/path/to/client.crt
        key=/path/to/client.key
        accesskey=your-access-key
        secretkey=your-secret-key
    </TestApp.HelloServer.HelloObj>
</client>
```

---

### Server 配置参数

所有服务端配置位于 `/tars/application/server` 路径下：

#### 基础服务配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `app` | string | UNKNOWN | 应用名称 |
| `server` | string | 可执行文件名 | 服务名称 |
| `localip` | string | 自动获取 | 本机IP地址 |
| `local` | string | - | 管理端口配置，格式：`tcp -h IP -p PORT -t TIMEOUT` |

#### 路径配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `basepath` | string | . | 基础路径（可执行文件路径） |
| `basepath.win` | string | - | Windows下的基础路径（优先级高于basepath） |
| `datapath` | string | . | 数据文件路径 |
| `datapath.win` | string | - | Windows下的数据路径 |
| `logpath` | string | . | 日志文件路径 |
| `logpath.win` | string | - | Windows下的日志路径 |

#### 日志配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `logsize` | string/int | 52428800 | 单个日志文件大小（支持K/M/G单位） |
| `lognum` | int | 10 | 日志文件保留个数 |
| `loglevel` | string | DEBUG | 日志级别：DEBUG/INFO/WARN/ERROR |
| `log` | string | - | 远程日志服务对象名，格式：`tars.tarslog.LogObj` |
| `closecout` | int | 1 | 是否关闭标准输出（0/1） |

#### Tars框架服务配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `node` | string | - | TarsNode服务地址 |
| `config` | string | - | 配置中心服务对象名，格式：`tars.tarsconfig.ConfigObj` |
| `notify` | string | - | 通知服务对象名，格式：`tars.tarsnotify.NotifyObj` |

#### 网络线程配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `netthread` | int | 1 | 服务端网络IO线程数，建议设置为CPU核心数 |
| `manuallisten` | int | 0 | 是否手动监听（0/1），用于服务启动后延迟监听端口 |

#### 协程配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `opencoroutine` | int | 0 | 是否启用协程（0/1） |
| `coroutinememsize` | string | 1G | 协程内存池总大小（支持K/M/G单位） |
| `coroutinestack` | string | 128K | 单个协程栈大小（支持K/M单位） |

**协程计算公式**：
```
最大协程数 = coroutinememsize / coroutinestack
例如: 1G / 128K = 8192个协程
```

#### 流量统计配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `reportflow` | int | 1 | 是否上报流量统计（0/1） |
| `checkset` | int | 1 | 是否检查SET合法性（0/1） |

#### 缓冲区配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `backpacketlimit` | int | 104857600 | 接收缓冲区上限（字节），默认100MB |
| `backpacketmin` | int | 1024 | 接收缓冲区最小值（字节） |

#### SSL/TLS配置

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ca` | string | - | CA证书文件路径 |
| `cert` | string | - | 服务端证书文件路径 |
| `key` | string | - | 服务端私钥文件路径 |
| `verifyclient` | int | 0 | 是否验证客户端证书（0/1） |
| `ciphers` | string | - | SSL密码套件 |

---

### Adapter 配置参数

每个Adapter配置位于 `/tars/application/server/<AdapterName>` 路径下：

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `endpoint` | string | 必填 | 监听端点，格式：`tcp -h IP -p PORT -t TIMEOUT` |
| `servant` | string | 必填 | 绑定的Servant对象名 |
| `threads` | int | 1 | 业务处理线程数 |
| `maxconns` | int | 128 | 最大连接数 |
| `queuecap` | int | 1024 | 请求队列容量 |
| `queuetimeout` | int | 10000 | 队列超时时间（毫秒） |
| `protocol` | string | tars | 协议类型：tars/http/json/grpc等 |
| `allow` | string | - | 允许访问的IP列表，多个用`;`或`,`分隔 |
| `deny` | string | - | 拒绝访问的IP列表，多个用`;`或`,`分隔 |
| `order` | string | allow,deny | 访问控制顺序：`allow,deny` 或 `deny,allow` |

**endpoint 格式说明**：
- TCP: `tcp -h 0.0.0.0 -p 8080 -t 60000`
- UDP: `udp -h 0.0.0.0 -p 8080 -t 60000`
- SSL: `ssl -h 0.0.0.0 -p 8080 -t 60000`

---

## 核心配置参数详解

### 1. 网络线程配置 (Network Threads)

#### 配置项：netthread
- **路径**: `/tars/application/server<netthread>` 或 `/tars/application/client<netthread>`
- **类型**: 整数
- **默认值**: 1（server）/ 1（client）
- **说明**: 控制网络IO处理线程数量
- **推荐值**: 
  - IO密集型：CPU核心数 × 2
  - CPU密集型：CPU核心数 × 1
  - 混合型：CPU核心数 × 1.5

**示例配置**:
```xml
<server>
    netthread=8          <!-- 8个网络线程 -->
</server>
```

### 2. 协程配置 (Coroutine Configuration)

#### 2.1 启用/禁用协程
- **配置项**: opencoroutine
- **路径**: `/tars/application/server<opencoroutine>`
- **类型**: 布尔值 (0/1)
- **默认值**: 0 (禁用)
- **说明**: 控制是否启用协程支持

#### 2.2 协程内存池大小
- **配置项**: coroutinememsize
- **路径**: `/tars/application/server<coroutinememsize>`
- **类型**: 字符串 (支持K, M, G单位)
- **默认值**: 1G
- **说明**: 协程池总内存大小

#### 2.3 协程栈大小
- **配置项**: coroutinestack
- **路径**: `/tars/application/server<coroutinestack>`
- **类型**: 字符串 (支持K, M单位)
- **默认值**: 128K
- **说明**: 单个协程栈大小

#### 2.4 计算最大协程数
```
最大协程数 = coroutinememsize / coroutinestack

示例：
coroutinememsize=2G
coroutinestack=128K
最大协程数 = 2GB / 128KB = 16,384个
```

### 3. 业务处理线程配置

#### 配置项：threads
- **路径**: `/tars/application/server/[AdapterName]<threads>`
- **类型**: 整数
- **默认值**: 1
- **说明**: 每个适配器的业务处理线程数

**示例配置**:
```xml
<server>
    <HelloAdapter>
        threads=10         <!-- 10个业务处理线程 -->
    </HelloAdapter>
</server>
```

### 4. 异步处理配置

#### 4.1 异步线程数
- **配置项**: asyncthread
- **路径**: `/tars/application/client<asyncthread>`
- **类型**: 整数
- **默认值**: 3
- **说明**: 处理异步回调的线程数量

#### 4.2 队列长度配置
- **配置项**: queuecap
- **路径**: `/tars/application/server/[AdapterName]<queuecap>`
- **类型**: 整数
- **默认值**: 1000000
- **说明**: 请求队列最大容量

## 场景化配置方案

### 场景1：高并发API网关
**特点**: 大量短连接，IO密集型

```xml
<tars>
  <application>
    <client>
        netthread=8              <!-- 网络线程 -->
        asyncthread=4            <!-- 异步线程 -->
    </client>
    
    <server>
        opencoroutine=1          <!-- 启用协程 -->
        coroutinememsize=2G      <!-- 2GB协程内存 -->
        coroutinestack=128K      <!-- 128KB栈大小 -->
        
        <GatewayAdapter>
            threads=16           <!-- 16个业务线程 -->
            maxconns=100000      <!-- 最大连接数 -->
            queuecap=500000      <!-- 队列容量 -->
        </GatewayAdapter>
    </server>
  </application>
</tars>
```

**性能预期**:
- 最大协程数: 15,625个
- 内存使用: ~2.5GB
- 支持并发: 50,000+QPS

### 场景2：实时消息推送服务
**特点**: 长连接，高并发

```xml
<tars>
  <application>
    <client>
        netthread=4              <!-- 网络线程 -->
    </client>
    
    <server>
        opencoroutine=1          <!-- 启用协程 -->
        coroutinememsize=4G      <!-- 4GB协程内存 -->
        coroutinestack=64K       <!-- 64KB小栈 -->
        
        <PushAdapter>
            threads=8            <!-- 8个业务线程 -->
            maxconns=1000000     <!-- 百万连接 -->
            queuecap=1000000     <!-- 大队列 -->
        </PushAdapter>
    </server>
  </application>
</tars>
```

**性能预期**:
- 最大协程数: 65,536个
- 内存使用: ~6GB
- 支持连接: 100万并发

### 场景3：计算密集型服务
**特点**: CPU计算为主，少量网络IO

```xml
<tars>
  <application>
    <client>
        netthread=2              <!-- 少量网络线程 -->
    </client>
    
    <server>
        opencoroutine=0          <!-- 禁用协程 -->
        
        <ComputeAdapter>
            threads=32           <!-- 更多CPU线程 -->
            maxconns=10000       <!-- 较少连接 -->
            queuecap=100000      <!-- 中等队列 -->
        </ComputeAdapter>
    </server>
  </application>
</tars>
```

## 配置验证与调试

### 1. 配置验证方法

#### 1.1 启动时验证
```bash
# 启动服务并查看配置日志
./HelloServer --config=config.conf | grep "Config"

# 查看实际生效的配置
./HelloServer --config=config.conf --print-config
```

#### 1.2 运行时验证
```bash
# 查看线程数量
ps -T -p [PID] | grep -E "(NetThread|HandleThread)"

# 查看内存使用
cat /proc/[PID]/status | grep -E "(VmRSS|VmSize)"

# 查看协程状态
./tarsadmin --coroutine-status
```

### 2. 代码中验证配置

```cpp
#include "servant/Application.h"

void checkConfig() {
    // 检查网络线程配置
    cout << "NetThread: " << ServerConfig::NetThread << endl;
    
    // 检查协程配置
    cout << "OpenCoroutine: " << ServerConfig::OpenCoroutine << endl;
    cout << "CoroutineMemSize: " << ServerConfig::CoroutineMemSize << endl;
    cout << "CoroutineStackSize: " << ServerConfig::CoroutineStackSize << endl;
    
    // 计算最大协程数
    size_t maxCoroutines = ServerConfig::CoroutineMemSize / ServerConfig::CoroutineStackSize;
    cout << "Max Coroutines: " << maxCoroutines << endl;
}
```

### 3. 调试参数

#### 3.1 开启调试日志
```xml
<server>
    debug=1
    tars-log-level=DEBUG
</server>
```

#### 3.2 性能监控配置
```xml
<server>
    # 启用性能统计
    deactivating=0
    sampleRate=1000
    maxSampleCount=10000
</server>
```

## 性能调优指南

### 1. 调优步骤

#### 步骤1：建立基线
```bash
# 基准测试
wrk -t12 -c400 -d30s http://localhost:8080/api
```

#### 步骤2：监控指标
- CPU使用率
- 内存使用量
- 网络吞吐量
- 响应延迟(P99, P95)

#### 步骤3：参数调整
根据监控结果，按以下顺序调整：

1. **网络线程** (netthread)
   - 网络IO瓶颈：增加netthread
   - CPU饱和：减少netthread

2. **协程配置**
   - 连接数多：增加coroutinememsize
   - 内存不足：减少coroutinestack

3. **业务线程** (threads)
   - CPU计算多：增加threads
   - IO等待多：减少threads，启用协程

### 2. 配置模板库

#### 模板1：微服务配置
```xml
<server>
    opencoroutine=1
    netthread=4
    coroutinememsize=1G
    coroutinestack=128K
    
    <${Adapter}>
        threads=8
        maxconns=50000
        queuecap=200000
    </${Adapter}>
</server>
```

#### 模板2：高并发配置
```xml
<server>
    opencoroutine=1
    netthread=8
    coroutinememsize=4G
    coroutinestack=64K
    
    <${Adapter}>
        threads=16
        maxconns=200000
        queuecap=1000000
    </${Adapter}>
</server>
```

## 常见问题解答

### Q1: 协程配置不生效怎么办？
**检查清单**:
1. 确认 `opencoroutine=1` 已设置
2. 检查 coroutinememsize 是否足够
3. 验证配置路径是否正确

### Q2: 内存使用过高如何处理？
**解决方案**:
1. 减少 `coroutinememsize`
2. 减小 `coroutinestack`
3. 降低 `maxconns`

### Q3: 网络线程数如何确定？
**经验公式**:
```
netthread = min(16, CPU核心数 × 2)
```

### Q4: 业务线程数如何优化？
**调试方法**:
```bash
# 查看线程CPU使用情况
pidstat -t -p [PID] 1

# 根据CPU使用率调整线程数
# CPU使用率 < 70%: 减少线程
# CPU使用率 > 90%: 增加线程
```

## 总结

通过合理配置TarsCpp的线程和协程参数，可以显著提升服务性能。关键要点：

1. **IO密集型**: 启用协程，增加网络线程
2. **CPU密集型**: 禁用协程，增加业务线程
3. **内存敏感**: 减小协程栈大小
4. **高并发**: 增加协程内存池
5. **持续监控**: 根据实际运行数据调整参数

记住：配置优化是一个持续过程，需要结合实际业务场景和监控数据不断调整。