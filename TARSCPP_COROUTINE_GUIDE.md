# TarsCpp 协程使用完全指南

## 目录
1. [协程概述](#协程概述)
2. [方式一：框架自动协程模式（推荐）](#方式一框架自动协程模式推荐)
3. [方式二：继承TC_Coroutine类](#方式二继承tc_coroutine类)
4. [方式三：使用TC_Thread + startCoroutine](#方式三使用tc_thread--startcoroutine)
5. [方式四：服务端协程并行调用](#方式四服务端协程并行调用)
6. [方式五：在已有协程中创建新协程](#方式五在已有协程中创建新协程)
7. [协程控制API](#协程控制api)
8. [线程与协程通信同步](#线程与协程通信同步)
9. [注意事项和最佳实践](#注意事项和最佳实践)

---

## 协程概述

TarsCpp从3.x版本开始全面支持协程，采用**单线程+协程调度**的模型：
- 每个线程有独立的协程调度器 (`TC_CoroutineScheduler`)
- 协程切换通过 `epoll` 实现，与网络IO无缝集成
- 写同步代码，享受异步性能

### 核心类

| 类名 | 说明 |
|------|------|
| `TC_CoroutineScheduler` | 协程调度器，管理协程的创建、调度和销毁 |
| `TC_Coroutine` | 协程封装类，继承自TC_Thread，便于业务使用 |
| `TC_Thread` | 线程类，支持普通线程和协程模式启动 |
| `CoroParallelBase` | 协程并行控制类，用于等待多个协程完成 |

---

## 方式一：框架自动协程模式（推荐）

### 适用场景
- Tars服务端业务代码
- 希望业务逻辑自动运行在协程中
- 最简单的使用方式

### 配置方式

在服务配置文件 `config.conf` 中启用协程：

```xml
<tars>
  <application>
    <server>
      # 启用协程
      opencoroutine=1
      # 最大协程数
      corothreadmax=1000
      # 协程栈大小（字节）
      corothreadstack=131072
    </server>
  </application>
</tars>
```

### 示例代码

```cpp
// YourServantImp.h
#include "servant/Application.h"
#include "YourServant.h"

class YourServantImp : public YourServant
{
public:
    virtual void initialize();
    virtual void destroy();
    
    // 业务接口实现
    virtual tars::Int32 doSomething(
        const std::string& request,
        std::string &response,
        tars::TarsCurrentPtr current);

private:
    OtherServicePrx _otherPrx;
};

// YourServantImp.cpp
void YourServantImp::initialize()
{
    // 初始化其他服务代理
    _otherPrx = Application::getCommunicator()->stringToProxy<OtherServicePrx>(
        "App.Server.Obj@tcp -h 127.0.0.1 -p 9000"
    );
}

tars::Int32 YourServantImp::doSomething(
    const std::string& request,
    std::string &response,
    tars::TarsCurrentPtr current)
{
    // ✅ 看起来是同步调用，实际在协程中自动yield/resume
    // ✅ 不会阻塞线程，其他协程可以继续执行
    
    try {
        // 调用其他服务1
        std::string result1;
        _otherPrx->method1(request, result1);
        
        // 调用其他服务2
        std::string result2;
        _otherPrx->method2(result1, result2);
        
        // 组装响应
        response = result2;
        return 0;
    }
    catch (const std::exception& e) {
        TLOGERROR("exception: " << e.what() << endl);
        return -1;
    }
}
```

### 特点
- ✅ 无需修改业务代码，只需配置
- ✅ 同步写法，异步执行
- ✅ 框架自动管理协程调度
- ✅ 性能最优

---

## 方式二：继承TC_Coroutine类

### 适用场景
- 需要创建独立的协程线程池
- 批量处理任务
- 需要精确控制协程数量和行为

### 完整示例

```cpp
#include "util/tc_coroutine.h"
#include "servant/Communicator.h"
#include <iostream>

using namespace tars;

// 1. 继承TC_Coroutine类
class MyCoroutineTask : public TC_Coroutine
{
public:
    MyCoroutineTask(int taskCount, const std::string& serverAddr)
        : _taskCount(taskCount)
    {
        // 初始化通信器和服务代理
        _prx = _comm.stringToProxy<YourServicePrx>(serverAddr);
    }
    
    virtual ~MyCoroutineTask() {}

protected:
    // 2. 实现handle方法（每个协程都会执行）
    virtual void handle() override
    {
        // 获取当前协程ID
        uint32_t coroId = getScheduler()->getCoroutineId();
        
        std::cout << "协程 " << coroId << " 开始执行" << std::endl;
        
        for (int i = 0; i < _taskCount; i++)
        {
            try
            {
                // 执行业务逻辑
                std::string request = "task_" + std::to_string(i);
                std::string response;
                
                int ret = _prx->processTask(request, response);
                
                if (ret == 0) {
                    std::cout << "协程 " << coroId 
                              << " 完成任务 " << i << std::endl;
                }
                
                // 主动让出CPU给其他协程
                yield();
                
                // 或者休眠一段时间
                // sleep(100);  // 休眠100ms
            }
            catch (const std::exception& e)
            {
                std::cerr << "协程 " << coroId 
                          << " 异常: " << e.what() << std::endl;
            }
        }
        
        std::cout << "协程 " << coroId << " 执行完成" << std::endl;
    }
    
    // 可选：线程启动前回调
    virtual void initialize() override
    {
        std::cout << "协程线程初始化" << std::endl;
    }
    
    // 可选：所有协程结束后回调
    virtual void destroy() override
    {
        std::cout << "协程线程销毁" << std::endl;
    }

private:
    int _taskCount;
    Communicator _comm;
    YourServicePrx _prx;
};

// 使用示例
int main(int argc, char* argv[])
{
    if (argc != 3) {
        std::cout << "Usage: " << argv[0] 
                  << " <task_count> <server_addr>" << std::endl;
        return -1;
    }
    
    int taskCount = std::stoi(argv[1]);
    std::string serverAddr = argv[2];
    
    // 3. 创建协程任务对象
    MyCoroutineTask coroTask(taskCount, serverAddr);
    
    // 4. 设置协程参数
    // setCoroInfo(同时运行的协程数, 协程池大小, 每个协程栈大小)
    coroTask.setCoroInfo(
        10,           // 同时启动10个协程执行handle方法
        100,          // 协程池最多容纳100个协程
        128 * 1024    // 每个协程栈128KB
    );
    
    // 5. 启动协程线程
    coroTask.start();
    
    // 6. 等待所有协程完成
    coroTask.getThreadControl().join();
    
    std::cout << "所有协程任务完成" << std::endl;
    
    return 0;
}
```

### 参数说明

```cpp
setCoroInfo(协程数量, 协程池大小, 栈大小);
```

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| 协程数量 | 同时有多少个协程在执行handle方法 | 根据并发需求，5-20 |
| 协程池大小 | 调度器最多管理多少个协程 | 协程数量的10-20倍 |
| 栈大小 | 每个协程的栈空间（字节） | 128KB（128*1024） |

---

## 方式三：使用TC_Thread + startCoroutine

### 适用场景
- 需要更灵活的协程控制
- 在线程中动态创建协程
- 不想受handle方法限制

### 示例代码

```cpp
#include "util/tc_thread.h"
#include "util/tc_coroutine.h"
#include <iostream>
#include <vector>

using namespace tars;

class MyFlexibleThread : public TC_Thread
{
public:
    MyFlexibleThread(int taskCount) : _taskCount(taskCount) {}
    
protected:
    virtual void run() override
    {
        // 获取当前线程的协程调度器
        auto scheduler = TC_CoroutineScheduler::scheduler();
        
        if (!scheduler) {
            std::cerr << "协程调度器未初始化" << std::endl;
            return;
        }
        
        std::cout << "线程启动，开始创建协程..." << std::endl;
        
        // 动态创建多个协程
        std::vector<uint32_t> coroIds;
        
        for (int i = 0; i < _taskCount; i++)
        {
            // 使用go方法创建协程
            uint32_t coroId = scheduler->go([i, this]() {
                this->processTask(i);
            });
            
            if (coroId > 0) {
                coroIds.push_back(coroId);
                std::cout << "创建协程 " << coroId 
                          << " 处理任务 " << i << std::endl;
            }
        }
        
        std::cout << "所有协程已创建，共 " 
                  << coroIds.size() << " 个" << std::endl;
    }
    
    void processTask(int taskId)
    {
        auto scheduler = TC_CoroutineScheduler::scheduler();
        
        std::cout << "协程开始处理任务 " << taskId << std::endl;
        
        // 模拟任务处理
        for (int i = 0; i < 5; i++)
        {
            std::cout << "任务 " << taskId 
                      << " 执行步骤 " << i << std::endl;
            
            // 休眠
            scheduler->sleep(100);
        }
        
        std::cout << "任务 " << taskId << " 完成" << std::endl;
    }

private:
    int _taskCount;
};

int main()
{
    MyFlexibleThread thread(10);
    
    // 以协程模式启动线程
    // startCoroutine(协程池大小, 栈大小, 自动退出)
    thread.startCoroutine(
        100,          // 协程池大小
        128 * 1024,   // 栈大小128KB
        true          // true: 所有协程结束后自动退出
    );
    
    thread.getThreadControl().join();
    
    std::cout << "线程结束" << std::endl;
    
    return 0;
}
```

---

## 方式四：服务端协程并行调用

### 适用场景
- 服务端需要并行调用多个下游服务
- 需要等待多个RPC调用全部完成
- 提高服务端性能

### ⚠️ 重要前提条件

**必须在协程环境中使用！**

`coro_xxx` 方法**必须在协程环境中调用**，否则会抛出 `TarsUseCoroException` 异常。

**启用协程的方式**：

1. **方式一：在 config.conf 中启用协程（推荐）**
```xml
<tars>
  <application>
    <server>
      opencoroutine=1
      corothreadmax=1000
      corothreadstack=131072
    </server>
  </application>
</tars>
```

2. **方式二：业务线程手动创建协程调度器**
```cpp
// 在业务线程中手动创建协程调度器
void yourBusinessThread()
{
    // 创建协程调度器
    auto scheduler = TC_CoroutineScheduler::create();
    scheduler->setPoolStackSize(100, 128 * 1024);
    
    // 启动协程
    scheduler->go([this]() {
        // 在这个协程中可以安全使用 coro_xxx
        CoroParallelBasePtr parallel = new CoroParallelBase(2);
        // ...
        _serviceA->coro_queryA(callback, request);
    });
    
    scheduler->run();
}
```

**检查是否在协程环境中**：
```cpp
// 检查当前线程是否有协程调度器
if (TC_CoroutineScheduler::scheduler() != nullptr) {
    // ✅ 可以安全使用 coro_xxx
    _serviceA->coro_queryA(callback, request);
} else {
    // ❌ 不能使用 coro_xxx，会抛出异常
    // 使用普通异步调用或同步调用
    _serviceA->async_queryA(callback, request);
}
```

### 完整示例

```cpp
// YourServantImp.h
#include "servant/Application.h"
#include "YourServant.h"

class YourServantImp : public YourServant
{
public:
    virtual void initialize();
    
    // 并行调用多个服务
    virtual tars::Int32 queryMultipleServices(
        const std::string& request,
        std::string &response,
        tars::TarsCurrentPtr current);

private:
    ServiceAPrx _serviceA;
    ServiceBPrx _serviceB;
    ServiceCPrx _serviceC;
};

// YourServantImp.cpp
#include "YourServantImp.h"

void YourServantImp::initialize()
{
    // 初始化多个服务代理
    _serviceA = Application::getCommunicator()->stringToProxy<ServiceAPrx>(
        "App.ServerA.Obj@tcp -h 127.0.0.1 -p 9001"
    );
    _serviceB = Application::getCommunicator()->stringToProxy<ServiceBPrx>(
        "App.ServerB.Obj@tcp -h 127.0.0.1 -p 9002"
    );
    _serviceC = Application::getCommunicator()->stringToProxy<ServiceCPrx>(
        "App.ServerC.Obj@tcp -h 127.0.0.1 -p 9003"
    );
}

// 定义回调类 - ServiceA
class ServiceACallback : public ServiceACoroPrxCallback
{
public:
    virtual void callback_queryA(tars::Int32 ret, const std::string& result) override
    {
        _ret = ret;
        _result = result;
    }
    
    virtual void callback_queryA_exception(tars::Int32 ret) override
    {
        _exception = ret;
    }
    
public:
    int _ret = -1;
    int _exception = 0;
    std::string _result;
};

// 定义回调类 - ServiceB
class ServiceBCallback : public ServiceBCoroPrxCallback
{
public:
    virtual void callback_queryB(tars::Int32 ret, const std::string& result) override
    {
        _ret = ret;
        _result = result;
    }
    
    virtual void callback_queryB_exception(tars::Int32 ret) override
    {
        _exception = ret;
    }
    
public:
    int _ret = -1;
    int _exception = 0;
    std::string _result;
};

// 定义回调类 - ServiceC
class ServiceCCallback : public ServiceCCoroPrxCallback
{
public:
    virtual void callback_queryC(tars::Int32 ret, const std::string& result) override
    {
        _ret = ret;
        _result = result;
    }
    
    virtual void callback_queryC_exception(tars::Int32 ret) override
    {
        _exception = ret;
    }
    
public:
    int _ret = -1;
    int _exception = 0;
    std::string _result;
};

tars::Int32 YourServantImp::queryMultipleServices(
    const std::string& request,
    std::string &response,
    tars::TarsCurrentPtr current)
{
    // ⚠️ 检查是否在协程环境中
    if (!TC_CoroutineScheduler::scheduler()) {
        TLOGERROR("coro_xxx methods require coroutine mode. "
                 << "Please enable coroutine in config.conf or run in coroutine context" << endl);
        return -1;
    }
    
    try
    {
        // 1. 创建并行控制器（3表示等待3个调用完成）
        CoroParallelBasePtr parallel = new CoroParallelBase(3);
        
        // 2. 创建回调对象并设置并行控制器
        TC_AutoPtr<ServiceACallback> cbA = new ServiceACallback();
        cbA->setCoroParallelBasePtr(parallel);
        
        TC_AutoPtr<ServiceBCallback> cbB = new ServiceBCallback();
        cbB->setCoroParallelBasePtr(parallel);
        
        TC_AutoPtr<ServiceCCallback> cbC = new ServiceCCallback();
        cbC->setCoroParallelBasePtr(parallel);
        
        // 3. 发起并行调用（使用coro_xxx方法）
        _serviceA->coro_queryA(cbA, request);
        _serviceB->coro_queryB(cbB, request);
        _serviceC->coro_queryC(cbC, request);
        
        // 4. 等待所有调用完成
        coroWhenAll(parallel);
        
        // 5. 检查结果
        if (cbA->_ret == 0 && cbB->_ret == 0 && cbC->_ret == 0 &&
            cbA->_exception == 0 && cbB->_exception == 0 && cbC->_exception == 0)
        {
            // 所有调用成功，合并结果
            response = "A:" + cbA->_result + 
                      "|B:" + cbB->_result + 
                      "|C:" + cbC->_result;
            
            TLOGDEBUG("并行调用成功" << endl);
            return 0;
        }
        else
        {
            TLOGERROR("并行调用部分失败: "
                     << "A=" << cbA->_ret << "/" << cbA->_exception
                     << ", B=" << cbB->_ret << "/" << cbB->_exception
                     << ", C=" << cbC->_ret << "/" << cbC->_exception << endl);
            return -1;
        }
    }
    catch (const std::exception& e)
    {
        TLOGERROR("并行调用异常: " << e.what() << endl);
        return -1;
    }
}
```

### 关键API

```cpp
// 1. 创建并行控制器
CoroParallelBasePtr parallel = new CoroParallelBase(N);  // N为等待的调用数量

// 2. 回调设置并行控制器
callback->setCoroParallelBasePtr(parallel);

// 3. 发起协程调用（注意是coro_xxx，不是普通调用）
proxy->coro_method(callback, params);

// 4. 等待所有完成
coroWhenAll(parallel);
```

### 非协程环境中的替代方案

如果服务未启用协程，无法使用 `coro_xxx` 方法，可以使用以下替代方案：

#### 方案1：使用普通异步调用 + 计数器

```cpp
tars::Int32 YourServantImp::queryMultipleServices(
    const std::string& request,
    std::string &response,
    tars::TarsCurrentPtr current)
{
    // 检查是否在协程环境
    if (!TC_CoroutineScheduler::scheduler()) {
        // 非协程环境，使用普通异步调用
        return queryMultipleServicesAsync(request, response, current);
    }
    
    // 协程环境，使用 coro_xxx
    // ... coro_xxx 代码 ...
}

// 非协程环境的实现
tars::Int32 YourServantImp::queryMultipleServicesAsync(
    const std::string& request,
    std::string &response,
    tars::TarsCurrentPtr current)
{
    // 使用原子计数器跟踪完成情况
    std::atomic<int> completedCount{0};
    std::atomic<bool> hasError{false};
    
    std::string resultA, resultB, resultC;
    int retA = -1, retB = -1, retC = -1;
    
    // 定义回调
    class AsyncCallback : public ServiceACoroPrxCallback {
    public:
        AsyncCallback(std::atomic<int>& count, std::atomic<bool>& error, 
                     std::string& result, int& ret)
            : _count(count), _error(error), _result(result), _ret(ret) {}
        
        virtual void callback_queryA(tars::Int32 ret, const std::string& r) override {
            _ret = ret;
            _result = r;
            if (ret != 0) _error.store(true);
            _count.fetch_add(1);
        }
        
        virtual void callback_queryA_exception(tars::Int32 ret) override {
            _ret = ret;
            _error.store(true);
            _count.fetch_add(1);
        }
        
    private:
        std::atomic<int>& _count;
        std::atomic<bool>& _error;
        std::string& _result;
        int& _ret;
    };
    
    // 发起异步调用
    TC_AutoPtr<AsyncCallback> cbA = new AsyncCallback(completedCount, hasError, resultA, retA);
    TC_AutoPtr<AsyncCallback> cbB = new AsyncCallback(completedCount, hasError, resultB, retB);
    TC_AutoPtr<AsyncCallback> cbC = new AsyncCallback(completedCount, hasError, resultC, retC);
    
    _serviceA->async_queryA(cbA, request);
    _serviceB->async_queryB(cbB, request);
    _serviceC->async_queryC(cbC, request);
    
    // 轮询等待（非协程环境）
    int timeout = 5000;  // 5秒超时
    int elapsed = 0;
    while (completedCount.load() < 3 && elapsed < timeout) {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
        elapsed += 10;
    }
    
    if (completedCount.load() < 3) {
        TLOGERROR("异步调用超时" << endl);
        return -1;
    }
    
    if (hasError.load() || retA != 0 || retB != 0 || retC != 0) {
        return -1;
    }
    
    response = "A:" + resultA + "|B:" + resultB + "|C:" + resultC;
    return 0;
}
```

#### 方案2：使用 Promise/Future（如果框架支持）

```cpp
// 如果 TarsCpp 支持 Promise，可以使用
tars::Future<std::string> futureA = _serviceA->promise_queryA(request);
tars::Future<std::string> futureB = _serviceB->promise_queryB(request);
tars::Future<std::string> futureC = _serviceC->promise_queryC(request);

// 等待所有完成
auto allResults = tars::WhenAll(futureA, futureB, futureC).get();
```

**推荐做法**：**在 config.conf 中启用协程**，这样最简单且性能最好！

---

## 方式五：在已有协程中创建新协程

### 适用场景
- 已经在协程环境中
- 需要动态创建子协程
- 实现协程的分治处理

### 示例代码

```cpp
#include "util/tc_coroutine.h"
#include <iostream>
#include <vector>

using namespace tars;

void processSubTask(int taskId, int subTaskId)
{
    auto scheduler = TC_CoroutineScheduler::scheduler();
    
    std::cout << "子协程处理 Task-" << taskId 
              << "-SubTask-" << subTaskId << std::endl;
    
    // 模拟处理
    scheduler->sleep(50);
    
    std::cout << "子协程完成 Task-" << taskId 
              << "-SubTask-" << subTaskId << std::endl;
}

void processMainTask(int taskId)
{
    auto scheduler = TC_CoroutineScheduler::scheduler();
    
    std::cout << "主协程 " << taskId << " 开始" << std::endl;
    
    // 在协程中创建多个子协程
    std::vector<uint32_t> subCoroIds;
    
    for (int i = 0; i < 5; i++)
    {
        // 创建子协程
        uint32_t coroId = scheduler->go([taskId, i]() {
            processSubTask(taskId, i);
        });
        
        if (coroId > 0) {
            subCoroIds.push_back(coroId);
        }
    }
    
    std::cout << "主协程 " << taskId 
              << " 创建了 " << subCoroIds.size() 
              << " 个子协程" << std::endl;
    
    // 主协程可以继续做其他事情
    scheduler->sleep(100);
    
    std::cout << "主协程 " << taskId << " 完成" << std::endl;
}

class MyCoroutineManager : public TC_Coroutine
{
public:
    MyCoroutineManager() {}
    
protected:
    virtual void handle() override
    {
        uint32_t coroId = getScheduler()->getCoroutineId();
        
        // 在handle中创建多个主协程
        for (int i = 0; i < 3; i++)
        {
            uint32_t mainCoroId = getScheduler()->go([i]() {
                processMainTask(i);
            });
            
            std::cout << "创建主协程 " << mainCoroId 
                      << " 处理任务 " << i << std::endl;
        }
        
        // 等待一段时间
        sleep(500);
    }
};

int main()
{
    MyCoroutineManager manager;
    
    manager.setCoroInfo(1, 50, 128 * 1024);
    manager.start();
    manager.getThreadControl().join();
    
    return 0;
}
```

---

## 协程控制API

### 基础API

```cpp
// 1. 获取当前线程的协程调度器
auto scheduler = TC_CoroutineScheduler::scheduler();

// 2. 创建协程
uint32_t coroId = scheduler->go(std::function<void()> callback);
// 返回值: >0 成功（协程ID），<=0 失败

// 3. 主动让出CPU（会被调度器自动唤醒）
scheduler->yield();

// 4. 休眠（毫秒）
scheduler->sleep(1000);  // 休眠1秒

// 5. 获取当前协程ID
uint32_t myId = scheduler->getCoroutineId();

// 6. 唤醒指定协程
scheduler->put(coroId);

// 7. 唤醒所有yield的协程
scheduler->notify();
```

### TC_Coroutine类方法

```cpp
class TC_Coroutine : public TC_Thread
{
public:
    // 设置协程参数
    void setCoroInfo(
        uint32_t iNum,      // 协程数量
        uint32_t iPoolSize, // 协程池大小
        size_t iStackSize   // 栈大小
    );
    
    // 创建协程（在已创建的协程中使用）
    uint32_t go(const std::function<void()>& coroFunc);
    
    // 当前协程让出CPU
    void yield();
    
    // 当前协程休眠（毫秒）
    void sleep(int millseconds);
    
    // 停止
    void terminate();
    
    // 获取设置的最大协程数
    uint32_t getMaxCoroNum();
    
    // 获取启动时设置的协程数
    uint32_t getCoroNum();
    
    // 获取协程栈大小
    size_t getCoroStackSize();
    
protected:
    // 需要实现的协程处理方法
    virtual void handle() = 0;
    
    // 可选：线程启动前回调
    virtual void initialize() {}
    
    // 可选：所有协程结束后回调
    virtual void destroy() {}
};
```

---

## 线程与协程通信同步

在 TarsCpp 的多线程+协程模型中，不同的通信场景需要使用不同的同步机制。本章节详细介绍各种同步方式的使用场景和注意事项。

### 8.1 通信场景分类

| 场景 | 推荐方案 | 注意事项 |
|------|---------|---------|
| **线程 → 协程** | `TC_ThreadQueue`（阻塞）<br>`TC_CasQueue`（非阻塞） | 业务线程投递任务给协程线程处理 |
| **协程 → 协程（同线程）** | `TC_CoroutineQueue`<br>直接调用（无需同步） | 同一调度器内的协程切换无需加锁 |
| **协程 → 协程（跨线程）** | `TC_CoroutineQueue`<br>`TC_ThreadQueue` | 跨线程需要线程安全保护 |
| **协程 → 线程** | `TC_ThreadQueue`<br>`std::atomic` | 协程向业务线程报告结果 |
| **简单状态共享** | `std::atomic` | 布尔标志、计数器等 |
| **短临界区保护** | `TC_SpinLock` | 锁持有时间 < 10μs |

---

### 8.2 TC_CoroutineQueue：协程间通信（推荐）

#### 特点
- ✅ **协程友好**：无数据时协程 yield，不阻塞线程
- ✅ **跨线程协程支持**：可以在不同线程的协程间传递数据
- ✅ **线程安全**：内部使用 `std::mutex` 保护
- ⚠️ **必须在协程中使用**：普通线程调用会导致异常

#### 使用示例：协程消费者-生产者模型

```cpp
#include "util/tc_coroutine.h"
#include "util/tc_coroutine_queue.h"
#include <iostream>

using namespace tars;

// 任务结构
struct Task {
    int taskId;
    std::string data;
};

class CoroutineWorker : public TC_Coroutine
{
public:
    CoroutineWorker() : _running(true) {}
    
    // 生产者：提交任务（可以从其他线程的协程调用）
    void submitTask(const Task& task)
    {
        _taskQueue.push_back(task, true);  // true 表示通知等待的协程
        std::cout << "提交任务: " << task.taskId << std::endl;
    }
    
    // 停止处理
    void shutdown()
    {
        _running.store(false);
        _taskQueue.terminate();  // 唤醒所有等待的协程
    }
    
protected:
    // 消费者：协程处理任务
    virtual void handle() override
    {
        uint32_t coroId = getScheduler()->getCoroutineId();
        std::cout << "协程 " << coroId << " 启动" << std::endl;
        
        // exec 会在有任务时执行回调，无任务时自动 yield
        _taskQueue.exec([this, coroId](const Task& task) {
            if (!_running.load()) {
                return;  // 退出处理
            }
            
            std::cout << "协程 " << coroId 
                      << " 处理任务 " << task.taskId 
                      << ": " << task.data << std::endl;
            
            // 模拟任务处理
            sleep(100);  // 协程休眠 100ms
            
            std::cout << "协程 " << coroId 
                      << " 完成任务 " << task.taskId << std::endl;
        });
        
        std::cout << "协程 " << coroId << " 退出" << std::endl;
    }

private:
    TC_CoroutineQueue<Task> _taskQueue;
    std::atomic<bool> _running;
};

// 使用示例
int main()
{
    CoroutineWorker worker;
    worker.setCoroInfo(3, 50, 128 * 1024);  // 3个协程处理任务
    worker.start();
    
    // 在主线程提交任务（需要主线程也在协程模式下）
    // 或者在另一个协程线程中提交
    for (int i = 0; i < 10; i++) {
        Task task;
        task.taskId = i;
        task.data = "data_" + std::to_string(i);
        worker.submitTask(task);
        
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    
    // 等待处理完成
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    worker.shutdown();
    worker.getThreadControl().join();
    
    return 0;
}
```

#### TC_CoroutineQueue 关键API

```cpp
// 放入数据（线程安全）
void push_back(const T& t, bool notify = true);   // 后端插入
void push_front(const T& t, bool notify = true);  // 前端插入

// 批量放入
void push_back(const queue_type& qt, bool notify = true);
void push_front(const queue_type& qt, bool notify = true);

// 消费数据（在协程中调用）
void exec(std::function<void(const T&)> func);  // 无数据时协程 yield

// 交换数据（非阻塞）
bool swap(queue_type& q);  // 返回 false 表示无数据

// 控制
void terminate();  // 结束队列，唤醒所有等待的协程
void notifyT();    // 通知所有等待的协程

// 查询
size_t size() const;
bool empty() const;
void clear();
```

---

### 8.3 TC_ThreadQueue：线程与协程通信

#### 特点
- ✅ **标准线程同步**：使用 `std::mutex` + `std::condition_variable`
- ✅ **阻塞等待支持**：支持带超时的阻塞获取
- ⚠️ **协程中避免阻塞**：在协程中调用阻塞方法会卡住整个线程
- ✅ **跨线程通信**：适合业务线程向协程线程投递任务

#### 使用示例：业务线程投递任务给协程

```cpp
#include "util/tc_thread_queue.h"
#include "util/tc_coroutine.h"
#include <thread>
#include <chrono>
#include <iostream>

using namespace tars;

struct BroadcastTask {
    int taskId;
    std::vector<int64_t> targetIds;
    std::string message;
};

class TaskDispatcher : public TC_Coroutine
{
public:
    TaskDispatcher() : _running(true) {}
    
    // ✅ 在业务线程中调用（线程安全）
    bool submitTask(BroadcastTask task)
    {
        if (!_running.load()) {
            return false;
        }
        
        // push_back 是线程安全的，可以从任何线程调用
        _taskQueue.push_back(std::move(task), true);  // 通知等待的线程
        return true;
    }
    
    void shutdown()
    {
        _running.store(false);
        _taskQueue.notifyT();  // 唤醒等待的线程/协程
    }
    
protected:
    virtual void handle() override
    {
        uint32_t coroId = getScheduler()->getCoroutineId();
        std::cout << "协程 " << coroId << " 启动" << std::endl;
        
        while (_running.load())
        {
            BroadcastTask task;
            
            // ⚠️ 方案1：阻塞获取（会阻塞线程，不推荐在协程中使用）
            // if (_taskQueue.pop_front(task, 1000, true)) {  // 等待 1000ms
            //     processTask(task);
            // }
            
            // ✅ 方案2：非阻塞轮询（协程友好）
            if (_taskQueue.pop_front(task, 0, false)) {  // 非阻塞获取
                processTask(task, coroId);
            } else {
                // 无数据，协程休眠后重试（不阻塞线程）
                sleep(10);  // 休眠 10ms
            }
        }
        
        std::cout << "协程 " << coroId << " 退出" << std::endl;
    }
    
    void processTask(const BroadcastTask& task, uint32_t coroId)
    {
        std::cout << "协程 " << coroId 
                  << " 处理任务 " << task.taskId 
                  << ", 目标数量: " << task.targetIds.size() 
                  << std::endl;
        
        // 处理任务...
        sleep(50);  // 模拟处理
    }

private:
    TC_ThreadQueue<BroadcastTask> _taskQueue;
    std::atomic<bool> _running;
};

// 使用示例
int main()
{
    TaskDispatcher dispatcher;
    dispatcher.setCoroInfo(5, 100, 128 * 1024);  // 5个协程
    dispatcher.start();
    
    // 业务线程投递任务
    std::thread businessThread([&dispatcher]() {
        for (int i = 0; i < 20; i++) {
            BroadcastTask task;
            task.taskId = i;
            task.targetIds = {1001, 1002, 1003};
            task.message = "broadcast_" + std::to_string(i);
            
            if (dispatcher.submitTask(std::move(task))) {
                std::cout << "业务线程提交任务 " << i << std::endl;
            }
            
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    });
    
    businessThread.join();
    
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    dispatcher.shutdown();
    dispatcher.getThreadControl().join();
    
    return 0;
}
```

#### TC_ThreadQueue 关键API

```cpp
// 放入数据（线程安全）
void push_back(const T& t, bool notify = true);
void push_front(const T& t, bool notify = true);

// 获取数据
bool pop_front(T& t, size_t millsecond = 0, bool wait = true);
// millsecond: 0=不阻塞, -1=永久等待, >0=等待指定毫秒数
// wait: false=非阻塞, true=阻塞等待

// 批量交换
bool swap(queue_type& q, size_t millsecond = 0, bool wait = true);

// 控制
void notifyT();  // 唤醒所有等待的线程
void clear();

// 查询
size_t size() const;
bool empty() const;
bool wait(size_t millsecond);  // 等待队列非空
```

---

### 8.4 TC_CasQueue：无锁高性能队列

#### 特点
- ✅ **无锁设计**：使用 `TC_SpinLock` 实现
- ✅ **高性能**：适合高频率、低延迟场景
- ✅ **非阻塞**：所有操作都是非阻塞的
- ⚠️ **消费者需要轮询**：无等待机制，需要主动轮询

#### 使用示例

```cpp
#include "util/tc_cas_queue.h"
#include "util/tc_coroutine.h"
#include <iostream>

using namespace tars;

struct HighFreqMessage {
    int64_t timestamp;
    int messageType;
    std::string payload;
};

class HighPerfProcessor : public TC_Coroutine
{
public:
    // 生产者（可以从任意线程调用）
    void sendMessage(const HighFreqMessage& msg)
    {
        _msgQueue.push_back(msg);  // 非阻塞，无锁
    }
    
protected:
    virtual void handle() override
    {
        uint32_t coroId = getScheduler()->getCoroutineId();
        
        while (true)
        {
            HighFreqMessage msg;
            
            // 非阻塞获取
            if (_msgQueue.pop_front(msg)) {
                processMessage(msg, coroId);
            } else {
                // 无数据，协程休眠短时间后重试
                sleep(1);  // 休眠 1ms（高频场景）
            }
        }
    }
    
    void processMessage(const HighFreqMessage& msg, uint32_t coroId)
    {
        std::cout << "协程 " << coroId 
                  << " 处理消息，类型: " << msg.messageType 
                  << ", 时间戳: " << msg.timestamp 
                  << std::endl;
    }

private:
    TC_CasQueue<HighFreqMessage> _msgQueue;
};
```

#### TC_CasQueue 关键API

```cpp
// 放入数据（非阻塞，线程安全）
void push_back(const T& t);
void push_front(const T& t);
void push_back(const queue_type& qt);
void push_front(const queue_type& qt);

// 获取数据（非阻塞）
bool pop_front(T& t);  // 返回 false 表示队列为空
bool pop_front();      // 仅弹出，不返回数据

// 交换数据（非阻塞）
bool swap(queue_type& q);

// 查询
size_t size() const;
bool empty() const;
void clear();
```

---

### 8.5 std::atomic：简单状态共享

#### 特点
- ✅ **无锁原子操作**：硬件级别的原子性保证
- ✅ **轻量级**：适合简单类型（bool, int, pointer 等）
- ✅ **协程和线程都适用**：不会阻塞
- ⚠️ **仅限简单类型**：不适合复杂对象

#### 使用示例

```cpp
#include <atomic>
#include <iostream>

class TaskProcessor
{
public:
    TaskProcessor() 
        : _running(true)
        , _processedCount(0)
        , _errorCount(0)
    {}
    
    // 从任意线程/协程调用
    void processTask()
    {
        if (!_running.load(std::memory_order_acquire)) {
            return;
        }
        
        // 原子递增
        _processedCount.fetch_add(1, std::memory_order_relaxed);
        
        // 业务处理...
        bool success = doWork();
        
        if (!success) {
            _errorCount.fetch_add(1, std::memory_order_relaxed);
        }
    }
    
    void stop()
    {
        // 原子设置停止标志
        _running.store(false, std::memory_order_release);
    }
    
    bool isRunning() const
    {
        return _running.load(std::memory_order_acquire);
    }
    
    void printStatistics() const
    {
        std::cout << "已处理: " << _processedCount.load() << std::endl;
        std::cout << "错误数: " << _errorCount.load() << std::endl;
    }

private:
    std::atomic<bool> _running;
    std::atomic<int64_t> _processedCount;
    std::atomic<int64_t> _errorCount;
    
    bool doWork() { /* ... */ return true; }
};
```

#### Memory Order 选择指南

```cpp
// 1. Relaxed：仅保证原子性，无同步语义（最快）
counter.fetch_add(1, std::memory_order_relaxed);

// 2. Acquire/Release：配对使用，保证数据依赖关系
// Release：写操作，所有之前的写操作对读线程可见
flag.store(true, std::memory_order_release);

// Acquire：读操作，读到 true 后能看到之前的写操作
if (flag.load(std::memory_order_acquire)) {
    // 可以安全访问之前写入的数据
}

// 3. Seq_cst：顺序一致性（默认，最慢但最安全）
flag.store(true);  // 等价于 memory_order_seq_cst
```

---

### 8.6 TC_SpinLock：短临界区保护

#### 特点
- ✅ **自旋等待**：避免线程切换开销
- ✅ **极低延迟**：适合锁持有时间 < 10μs 的场景
- ⚠️ **不可长时间持有**：会占用 CPU 自旋等待
- ⚠️ **协程中谨慎使用**：可能导致其他协程饥饿

#### 使用示例

```cpp
#include "util/tc_spin_lock.h"
#include <iostream>

using namespace tars;

class ConnectionManager
{
public:
    // 快速更新连接状态
    void updateConnectionState(int64_t connId, int state)
    {
        TC_LockT<TC_SpinLock> lock(_spinLock);  // 自动加锁/解锁
        
        // 极短的临界区（< 10μs）
        _connectionStates[connId] = state;
        _lastUpdateTime = getCurrentTime();
        
    }  // 自动解锁
    
    int getConnectionState(int64_t connId)
    {
        TC_LockT<TC_SpinLock> lock(_spinLock);
        
        auto it = _connectionStates.find(connId);
        return (it != _connectionStates.end()) ? it->second : -1;
    }

private:
    mutable TC_SpinLock _spinLock;
    std::unordered_map<int64_t, int> _connectionStates;
    int64_t _lastUpdateTime;
    
    int64_t getCurrentTime() { return 0; /* ... */ }
};
```

#### 适用场景判断

```cpp
// ✅ 适合使用 TC_SpinLock 的场景：
// - 更新计数器
// - 读写缓存索引
// - 更新简单状态标志
// - 操作小型哈希表
// - 临界区代码 < 10 行，无函数调用

// ❌ 不适合使用 TC_SpinLock 的场景：
// - 临界区包含 I/O 操作
// - 临界区有函数调用或复杂计算
// - 临界区可能被长时间持有
// - 高竞争场景（多个线程频繁争抢）
```

---

### 8.7 std::mutex + std::condition_variable：传统同步（慎用）

#### ⚠️ 重要警告

在协程中使用 `std::condition_variable::wait()` 会**阻塞整个线程**，导致该线程上的所有协程都无法执行！

#### 适用场景

- ✅ 业务线程向协程线程投递任务（仅 notify，不 wait）
- ✅ 协程线程向业务线程发送通知（仅 notify，不 wait）
- ❌ 协程中等待条件变量（会阻塞线程）

#### 正确使用示例：业务线程等待，协程通知

```cpp
#include <mutex>
#include <condition_variable>
#include <deque>
#include "util/tc_coroutine.h"

// 业务线程投递任务，协程线程处理
class HybridDispatcher : public TC_Coroutine
{
public:
    // ✅ 业务线程调用：投递任务
    bool submitTask(Task task)
    {
        {
            std::lock_guard<std::mutex> lock(_mutex);
            if (_tasks.size() >= 1000) {
                return false;  // 队列满
            }
            _tasks.emplace_back(std::move(task));
        }
        // ✅ 仅通知，不等待
        _condition.notify_one();
        return true;
    }
    
protected:
    virtual void handle() override
    {
        while (_running.load())
        {
            Task task;
            bool hasTask = false;
            
            // ⚠️ 错误做法：在协程中阻塞等待
            // {
            //     std::unique_lock<std::mutex> lock(_mutex);
            //     _condition.wait(lock, [this]() {  // ❌ 会阻塞整个线程！
            //         return !_tasks.empty() || !_running;
            //     });
            //     ...
            // }
            
            // ✅ 正确做法：非阻塞检查 + 协程休眠
            {
                std::lock_guard<std::mutex> lock(_mutex);
                if (!_tasks.empty()) {
                    task = std::move(_tasks.front());
                    _tasks.pop_front();
                    hasTask = true;
                }
            }
            
            if (hasTask) {
                processTask(task);
            } else {
                // 协程休眠（不阻塞线程）
                sleep(10);  // 10ms
            }
        }
    }

private:
    std::mutex _mutex;
    std::condition_variable _condition;  // 仅用于通知，不在协程中 wait
    std::deque<Task> _tasks;
    std::atomic<bool> _running{true};
    
    void processTask(const Task& task) { /* ... */ }
};
```

#### 正确使用示例：协程通知业务线程

```cpp
class ResultCollector
{
public:
    // ✅ 协程调用：提交结果并通知
    void submitResult(int taskId, std::string result)
    {
        {
            std::lock_guard<std::mutex> lock(_mutex);
            _results[taskId] = std::move(result);
        }
        // ✅ 仅通知，不等待
        _condition.notify_one();
    }
    
    // ✅ 业务线程调用：等待结果
    bool waitForResult(int taskId, std::string& result, int timeoutMs)
    {
        std::unique_lock<std::mutex> lock(_mutex);
        
        // ✅ 业务线程中可以安全地 wait
        bool success = _condition.wait_for(lock, 
            std::chrono::milliseconds(timeoutMs),
            [this, taskId]() {
                return _results.find(taskId) != _results.end();
            });
        
        if (success) {
            result = _results[taskId];
            _results.erase(taskId);
        }
        
        return success;
    }

private:
    std::mutex _mutex;
    std::condition_variable _condition;
    std::unordered_map<int, std::string> _results;
};
```

---

### 8.8 方案对比与选择指南

#### 快速选择表

| 你的场景 | 推荐方案 | 理由 |
|---------|---------|------|
| 业务线程投递任务给协程 | `TC_ThreadQueue`（非阻塞模式） | 线程安全，协程中非阻塞获取 |
| 协程间传递任务（同线程） | `TC_CoroutineQueue` | 协程友好，自动 yield |
| 协程间传递任务（跨线程） | `TC_CoroutineQueue` | 支持跨线程协程 |
| 高频消息传递 | `TC_CasQueue` | 无锁，高性能 |
| 简单标志位/计数器 | `std::atomic` | 轻量，无阻塞 |
| 保护极短临界区 | `TC_SpinLock` | 低延迟 |
| 业务线程等待协程结果 | `std::mutex + std::condition_variable` | 业务线程可以安全 wait |

#### 性能对比

```cpp
// 性能测试数据（仅供参考）
// 测试环境：Intel i7, 8核, Linux 5.x

// 1. 单次操作延迟（纳秒）
std::atomic<int>:              ~5ns    (最快)
TC_SpinLock (无竞争):         ~20ns
TC_CasQueue::push_back():     ~50ns
TC_CoroutineQueue::push_back(): ~200ns
TC_ThreadQueue::push_back():   ~300ns
std::mutex (无竞争):          ~25ns
std::mutex (有竞争):          ~1000ns+ (最慢)

// 2. QPS（每秒操作数，多线程场景）
TC_CasQueue:            ~10M QPS
TC_CoroutineQueue:      ~5M QPS
TC_ThreadQueue:         ~3M QPS
std::mutex:             ~1M QPS
```

#### 决策流程图

```
开始
  |
  ├─ 是否只是简单标志/计数？
  |   └─ 是 → 使用 std::atomic
  |
  ├─ 是否跨线程通信？
  |   ├─ 是 → 是否需要阻塞等待？
  |   |   ├─ 是（业务线程等待）→ TC_ThreadQueue + 业务线程 wait
  |   |   └─ 否 → TC_CasQueue（高频）或 TC_ThreadQueue（通用）
  |   |
  |   └─ 否 → 同线程协程间通信？
  |       └─ 是 → TC_CoroutineQueue
  |
  └─ 是否极短临界区（< 10μs）？
      ├─ 是 → TC_SpinLock
      └─ 否 → 重新设计，避免锁
```

---

### 8.9 完整实战示例：广播系统

以下是一个完整的示例，展示了业务线程、协程线程之间的通信：

```cpp
#include "util/tc_coroutine.h"
#include "util/tc_cas_queue.h"
#include <thread>
#include <atomic>
#include <vector>
#include <iostream>

using namespace tars;

// 广播任务
struct BroadcastTask {
    int taskId;
    std::vector<int64_t> connectionIds;
    std::string message;
};

// 广播结果
struct BroadcastResult {
    int taskId;
    int successCount;
    int failureCount;
};

// 广播分发器（协程处理）
class BroadcastDispatcher : public TC_Coroutine
{
public:
    BroadcastDispatcher(TC_CasQueue<BroadcastResult>& resultQueue)
        : _resultQueue(resultQueue)
        , _running(true)
    {}
    
    // ✅ 业务线程调用：提交广播任务
    bool submitTask(BroadcastTask task)
    {
        if (!_running.load(std::memory_order_acquire)) {
            return false;
        }
        
        // 高性能无锁队列投递
        _taskQueue.push_back(std::move(task));
        
        _submitCount.fetch_add(1, std::memory_order_relaxed);
        return true;
    }
    
    void shutdown()
    {
        _running.store(false, std::memory_order_release);
    }
    
    int64_t getSubmitCount() const
    {
        return _submitCount.load(std::memory_order_relaxed);
    }
    
protected:
    virtual void handle() override
    {
        uint32_t coroId = getScheduler()->getCoroutineId();
        std::cout << "广播协程 " << coroId << " 启动" << std::endl;
        
        while (_running.load(std::memory_order_acquire))
        {
            BroadcastTask task;
            
            // ✅ 非阻塞获取任务（协程友好）
            if (_taskQueue.pop_front(task)) {
                processBroadcast(task, coroId);
            } else {
                // 无任务，协程休眠（不阻塞线程）
                sleep(10);
            }
        }
        
        std::cout << "广播协程 " << coroId << " 退出" << std::endl;
    }
    
    void processBroadcast(const BroadcastTask& task, uint32_t coroId)
    {
        std::cout << "协程 " << coroId 
                  << " 处理广播任务 " << task.taskId
                  << ", 目标数量: " << task.connectionIds.size()
                  << std::endl;
        
        BroadcastResult result;
        result.taskId = task.taskId;
        result.successCount = 0;
        result.failureCount = 0;
        
        // 并发发送给所有连接
        for (size_t i = 0; i < task.connectionIds.size(); i += 10)
        {
            // 批量发送（每次10个）
            for (size_t j = i; j < std::min(i + 10, task.connectionIds.size()); j++)
            {
                // 创建子协程并发发送
                getScheduler()->go([this, &task, &result, j]() {
                    bool success = sendToConnection(task.connectionIds[j], task.message);
                    if (success) {
                        result.successCount++;
                    } else {
                        result.failureCount++;
                    }
                });
            }
            
            // 让出 CPU，让子协程执行
            yield();
        }
        
        // 等待所有子协程完成（简化处理）
        sleep(100);
        
        // ✅ 发送结果给业务线程（无锁）
        _resultQueue.push_back(result);
        
        _processedCount.fetch_add(1, std::memory_order_relaxed);
    }
    
    bool sendToConnection(int64_t connId, const std::string& message)
    {
        // 模拟发送（协程中的网络 IO 不会阻塞线程）
        sleep(10);
        return true;
    }

private:
    TC_CasQueue<BroadcastTask> _taskQueue;            // 任务队列（无锁）
    TC_CasQueue<BroadcastResult>& _resultQueue;       // 结果队列（无锁）
    std::atomic<bool> _running;
    std::atomic<int64_t> _submitCount{0};
    std::atomic<int64_t> _processedCount{0};
};

// 业务线程：提交任务并收集结果
void businessThread(BroadcastDispatcher& dispatcher, 
                   TC_CasQueue<BroadcastResult>& resultQueue)
{
    std::cout << "业务线程启动" << std::endl;
    
    // 提交任务
    for (int i = 0; i < 20; i++)
    {
        BroadcastTask task;
        task.taskId = i;
        task.message = "broadcast_message_" + std::to_string(i);
        
        // 生成目标连接列表
        for (int j = 0; j < 50; j++) {
            task.connectionIds.push_back(i * 1000 + j);
        }
        
        if (dispatcher.submitTask(std::move(task))) {
            std::cout << "业务线程提交任务 " << i << std::endl;
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    std::cout << "业务线程：所有任务已提交" << std::endl;
    
    // 收集结果
    int totalSuccess = 0;
    int totalFailure = 0;
    int resultCount = 0;
    
    while (resultCount < 20)
    {
        BroadcastResult result;
        
        // ✅ 非阻塞获取结果，未取到则短暂休眠后继续轮询
        if (resultQueue.pop_front(result)) {
            std::cout << "收到结果：任务 " << result.taskId
                      << ", 成功: " << result.successCount
                      << ", 失败: " << result.failureCount
                      << std::endl;
            
            totalSuccess += result.successCount;
            totalFailure += result.failureCount;
            resultCount++;
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
    }
    
    std::cout << "业务线程：统计完成" << std::endl;
    std::cout << "总成功: " << totalSuccess << std::endl;
    std::cout << "总失败: " << totalFailure << std::endl;
}

int main()
{
    // 结果队列（协程 → 业务线程，使用无锁队列）
    TC_CasQueue<BroadcastResult> resultQueue;
    
    // 启动广播协程
    BroadcastDispatcher dispatcher(resultQueue);
    dispatcher.setCoroInfo(5, 100, 256 * 1024);  // 5个协程
    dispatcher.start();
    
    // 启动业务线程
    std::thread business(businessThread, std::ref(dispatcher), std::ref(resultQueue));
    
    // 等待业务线程完成
    business.join();
    
    // 关闭协程
    std::this_thread::sleep_for(std::chrono::seconds(1));
    dispatcher.shutdown();
    dispatcher.getThreadControl().join();
    
    std::cout << "程序结束" << std::endl;
    
    return 0;
}
```

---

## 注意事项和最佳实践

### ⚠️ 禁止事项

#### 1. 不要在非协程环境中使用 coro_xxx 方法

```cpp
// ❌ 错误：在普通业务线程中调用（未启用协程）
tars::Int32 YourServantImp::someMethod(..., tars::TarsCurrentPtr current)
{
    // 如果 config.conf 中没有 opencoroutine=1
    // 这里会抛出 TarsUseCoroException 异常！
    _serviceA->coro_queryA(callback, request);  // ❌ 异常！
}

// ✅ 正确方式1：在 config.conf 中启用协程
// config.conf:
// opencoroutine=1
// corothreadmax=1000
tars::Int32 YourServantImp::someMethod(..., tars::TarsCurrentPtr current)
{
    // 框架自动在协程环境中运行，可以安全使用
    _serviceA->coro_queryA(callback, request);  // ✅ 安全
}

// ✅ 正确方式2：检查协程环境
tars::Int32 YourServantImp::someMethod(..., tars::TarsCurrentPtr current)
{
    if (TC_CoroutineScheduler::scheduler()) {
        // 在协程环境中，使用 coro_xxx
        _serviceA->coro_queryA(callback, request);
    } else {
        // 不在协程环境，使用普通异步调用
        _serviceA->async_queryA(callback, request);
    }
}
```

**关键点**：
- `coro_xxx` 方法**必须在协程环境中调用**
- 如果服务未启用协程，会抛出 `TarsUseCoroException("coroutine mode invoke not open")`
- 使用前检查：`TC_CoroutineScheduler::scheduler() != nullptr`

#### 2. 不要使用阻塞式同步原语

```cpp
// ❌ 错误：会阻塞整个线程
std::mutex _mutex;
void badExample()
{
    std::lock_guard<std::mutex> lock(_mutex);  // 会阻塞所有协程
    // ...
}

// ✅ 正确：使用协程友好的同步机制
TC_CoroutineQueue<Task> _queue;
void goodExample()
{
    Task task;
    _queue.pop_front(task);  // 协程安全的阻塞
    // ...
}
```

**禁止使用的类型**：
- `std::mutex`
- `std::condition_variable`
- `TC_ThreadMutex`
- `TC_ThreadRecMutex`
- `pthread_mutex_t`

**推荐使用的类型**：
- `TC_CoroutineQueue` - 协程队列
- `std::atomic` - 原子操作
- 无锁队列
- `TC_SpinLock`（谨慎使用）

#### 2. 不要在协程中进行阻塞IO

```cpp
// ❌ 错误：阻塞IO会卡住整个线程
void badExample()
{
    FILE* fp = fopen("file.txt", "r");
    char buffer[1024];
    fgets(buffer, sizeof(buffer), fp);  // 阻塞读取
    fclose(fp);
}

// ✅ 正确：使用异步IO或放在独立线程池
void goodExample()
{
    // 方案1：放到线程池处理
    _ioThreadPool->exec([this]() {
        FILE* fp = fopen("file.txt", "r");
        // ...处理...
        fclose(fp);
    });
    
    // 方案2：使用异步IO库
    // async_read_file(...);
}
```

### ✅ 最佳实践

#### 1. 栈大小选择

```cpp
// 不同场景的栈大小建议
setCoroInfo(10, 100, 64 * 1024);    // 简单任务：64KB
setCoroInfo(10, 100, 128 * 1024);   // 一般任务：128KB（推荐）
setCoroInfo(10, 100, 256 * 1024);   // 复杂任务：256KB
setCoroInfo(10, 100, 512 * 1024);   // 深度递归：512KB
```

#### 2. 协程数量规划

```cpp
// 协程数量计算公式
// 协程数 = min(并发请求数, CPU核心数 * 10)
// 协程池大小 = 协程数 * 10~20

int cpuCount = std::thread::hardware_concurrency();
int coroCount = std::min(expectedConcurrency, cpuCount * 10);
int poolSize = coroCount * 15;

setCoroInfo(coroCount, poolSize, 128 * 1024);
```

#### 3. 异常处理

```cpp
virtual void handle() override
{
    try
    {
        // 协程业务代码
        doBusinessLogic();
    }
    catch (const TarsException& e)
    {
        // 捕获Tars异常
        TLOGERROR("TarsException: " << e.what() << endl);
    }
    catch (const std::exception& e)
    {
        // 捕获标准异常
        TLOGERROR("std::exception: " << e.what() << endl);
    }
    catch (...)
    {
        // 捕获所有异常
        TLOGERROR("Unknown exception" << endl);
    }
}
```

#### 4. 资源清理

```cpp
class MyCoroutineTask : public TC_Coroutine
{
public:
    MyCoroutineTask()
    {
        _running.store(true);
    }
    
    virtual void destroy() override
    {
        // 设置停止标志
        _running.store(false);
        
        // 清理资源
        _comm.terminate();
        
        std::cout << "资源清理完成" << std::endl;
    }
    
protected:
    virtual void handle() override
    {
        while (_running.load())
        {
            // 业务处理
            processTask();
            
            // 检查停止标志
            if (!_running.load()) {
                break;
            }
            
            yield();
        }
    }
    
private:
    std::atomic<bool> _running;
    Communicator _comm;
};
```

#### 5. 性能监控

```cpp
virtual void handle() override
{
    uint32_t coroId = getScheduler()->getCoroutineId();
    int64_t startTime = TC_Common::now2ms();
    
    // 业务处理
    processTask();
    
    int64_t costTime = TC_Common::now2ms() - startTime;
    
    // 记录性能指标
    if (costTime > 1000) {
        TLOGWARN("协程 " << coroId 
                 << " 执行时间过长: " << costTime << "ms" << endl);
    }
}
```

### 📊 性能对比

| 模式 | QPS | 延迟 | 内存占用 | 适用场景 |
|------|-----|------|---------|---------|
| 纯线程 | 10K | 10ms | 高（每线程1-2MB） | CPU密集型 |
| 线程+协程 | 50K | 5ms | 中（每协程128KB） | 混合型 |
| 纯协程 | 100K+ | 2ms | 低 | IO密集型 |

### 🔧 调试技巧

```cpp
// 1. 打印协程信息
auto scheduler = TC_CoroutineScheduler::scheduler();
if (scheduler) {
    uint32_t coroId = scheduler->getCoroutineId();
    std::cout << "当前协程ID: " << coroId << std::endl;
}

// 2. 添加调试日志
#define CORO_DEBUG(msg) \
    TLOGDEBUG("[Coro-" << TC_CoroutineScheduler::scheduler()->getCoroutineId() \
              << "] " << msg << endl)

CORO_DEBUG("开始处理任务");

// 3. 统计协程使用情况
class MyCoroutine : public TC_Coroutine
{
private:
    std::atomic<int> _activeCount{0};
    std::atomic<int> _totalProcessed{0};
    
protected:
    virtual void handle() override
    {
        _activeCount.fetch_add(1);
        
        // 业务处理
        processTask();
        
        _totalProcessed.fetch_add(1);
        _activeCount.fetch_sub(1);
        
        // 定期输出统计
        if (_totalProcessed % 1000 == 0) {
            std::cout << "活跃协程: " << _activeCount 
                      << ", 已处理: " << _totalProcessed << std::endl;
        }
    }
};
```

---

## 完整示例：高性能HTTP代理

```cpp
#include "util/tc_coroutine.h"
#include "servant/Communicator.h"
#include "util/tc_http.h"
#include <iostream>

using namespace tars;

class HttpProxyCoroutine : public TC_Coroutine
{
public:
    HttpProxyCoroutine(int requestCount)
        : _requestCount(requestCount)
        , _successCount(0)
        , _failureCount(0)
    {
        // 初始化后端服务代理
        _backendPrx = _comm.stringToProxy<BackendServicePrx>(
            "App.Backend.Obj@tcp -h 127.0.0.1 -p 9000"
        );
    }
    
    void printStatistics()
    {
        std::cout << "\n========== 统计信息 ==========" << std::endl;
        std::cout << "总请求数: " << _requestCount << std::endl;
        std::cout << "成功: " << _successCount << std::endl;
        std::cout << "失败: " << _failureCount << std::endl;
        std::cout << "成功率: " 
                  << (100.0 * _successCount / _requestCount) 
                  << "%" << std::endl;
    }
    
protected:
    virtual void initialize() override
    {
        std::cout << "HTTP代理协程初始化" << std::endl;
    }
    
    virtual void handle() override
    {
        uint32_t coroId = getScheduler()->getCoroutineId();
        int64_t startTime = TC_Common::now2ms();
        
        try
        {
            // 模拟HTTP请求
            TC_HttpRequest request;
            request.setPostRequest("http://backend/api", "request_data");
            
            // 转发到后端服务（协程模式下自动yield）
            std::string response;
            int ret = _backendPrx->processRequest(
                request.encode(), 
                response
            );
            
            if (ret == 0) {
                _successCount.fetch_add(1);
                
                // 处理响应
                TC_HttpResponse httpRsp;
                httpRsp.decode(response);
                
                TLOGDEBUG("协程-" << coroId 
                         << " 请求成功，状态码: " 
                         << httpRsp.getStatus() << endl);
            }
            else {
                _failureCount.fetch_add(1);
                TLOGERROR("协程-" << coroId << " 请求失败" << endl);
            }
        }
        catch (const std::exception& e)
        {
            _failureCount.fetch_add(1);
            TLOGERROR("协程-" << coroId 
                     << " 异常: " << e.what() << endl);
        }
        
        int64_t costTime = TC_Common::now2ms() - startTime;
        
        // 记录慢请求
        if (costTime > 1000) {
            TLOGWARN("协程-" << coroId 
                    << " 慢请求: " << costTime << "ms" << endl);
        }
        
        // 让出CPU
        yield();
    }
    
    virtual void destroy() override
    {
        std::cout << "HTTP代理协程销毁" << std::endl;
        printStatistics();
    }
    
private:
    int _requestCount;
    std::atomic<int> _successCount;
    std::atomic<int> _failureCount;
    Communicator _comm;
    BackendServicePrx _backendPrx;
};

int main(int argc, char* argv[])
{
    if (argc != 4) {
        std::cout << "Usage: " << argv[0] 
                  << " <request_count> <coro_num> <pool_size>" 
                  << std::endl;
        return -1;
    }
    
    int requestCount = std::stoi(argv[1]);
    int coroNum = std::stoi(argv[2]);
    int poolSize = std::stoi(argv[3]);
    
    std::cout << "启动HTTP代理，配置:" << std::endl;
    std::cout << "- 总请求数: " << requestCount << std::endl;
    std::cout << "- 协程数: " << coroNum << std::endl;
    std::cout << "- 协程池: " << poolSize << std::endl;
    
    HttpProxyCoroutine proxy(requestCount);
    
    // 设置协程参数
    proxy.setCoroInfo(coroNum, poolSize, 128 * 1024);
    
    // 启动
    int64_t startTime = TC_Common::now2ms();
    proxy.start();
    proxy.getThreadControl().join();
    int64_t totalTime = TC_Common::now2ms() - startTime;
    
    std::cout << "\n总耗时: " << totalTime << "ms" << std::endl;
    std::cout << "QPS: " << (requestCount * 1000.0 / totalTime) << std::endl;
    
    return 0;
}
```

---

## 参考资料

- TarsCpp官方文档: https://github.com/TarsCloud/TarsCpp
- 协程示例代码: `examples/CoroutineDemo/`
- 协程头文件: `util/include/util/tc_coroutine.h`

---

**版本**: TarsCpp 3.x+  
**更新日期**: 2024-11  
**作者**: TarsCpp开发团队

