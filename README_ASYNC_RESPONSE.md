# TarsCpp 服务端异步响应完全指南

## 目录
- [一、概述](#一概述)
- [二、基本原理](#二基本原理)
- [三、完整示例](#三完整示例)
- [四、串行调用场景](#四串行调用场景)
- [五、并行调用场景](#五并行调用场景)
- [六、关键API说明](#六关键api说明)
- [七、执行流程](#七执行流程)
- [八、最佳实践](#八最佳实践)
- [九、常见问题](#九常见问题)

---

## 一、概述

### 1.1 什么是服务端异步响应

服务端异步响应是一种让服务端接口**立即返回**、不阻塞线程，然后在异步回调中再响应客户端的技术。这是实现高并发、非阻塞服务的关键方法。

### 1.2 核心优势

- ✅ **非阻塞**：服务端线程立即释放，可处理更多请求
- ✅ **高并发**：单线程可同时处理多个请求
- ✅ **灵活控制**：可在任意时机响应客户端
- ✅ **支持复杂流程**：串行调用、并行调用、条件分支等

### 1.3 适用场景

- 需要调用多个下游服务
- 下游服务响应时间较长
- 需要高并发处理能力
- 需要复杂的业务编排（串行、并行、条件）

---

## 二、基本原理

### 2.1 传统同步模式（阻塞）

```cpp
// 客户端请求 → 服务端处理 → 返回响应
tars::Int32 YourServantImp::doSomething(
    const std::string& request,
    std::string &response,
    tars::TarsCurrentPtr current)
{
    // ❌ 阻塞等待下游服务
    _otherPrx->method1(request, response);
    
    // 函数返回时，框架自动发送响应给客户端
    return 0;
}
```

**问题**：如果 `method1` 调用耗时长（如100ms），当前线程被阻塞，无法处理其他请求。

**性能影响**：
- 单线程 QPS = 1000ms / 100ms = 10 QPS
- 需要大量线程才能支撑高并发

### 2.2 异步响应模式（非阻塞）

```cpp
tars::Int32 YourServantImp::doSomething(
    const std::string& request,
    std::string &response,
    tars::TarsCurrentPtr current)
{
    // ✅ 关键步骤1：告诉框架不要自动响应
    current->setResponse(false);
    
    // ✅ 关键步骤2：发起异步调用（立即返回）
    MyCallbackPtr callback = new MyCallback(current);
    _otherPrx->async_method1(callback, request);
    
    // ✅ 关键步骤3：立即返回，不阻塞线程
    return 0;
}

// ✅ 关键步骤4：在回调中响应客户端
void MyCallback::callback_method1(int ret, const std::string& result) {
    // 手动响应客户端
    YourServant::async_response_doSomething(_current, ret, result);
}
```

**优势**：
- 函数立即返回（耗时 < 1ms）
- 线程可以立即处理下一个请求
- 单线程 QPS 可达数千甚至上万

**性能提升**：
- 传统模式：10 QPS/线程
- 异步模式：1000+ QPS/线程（提升100倍）

---

## 三、完整示例

### 3.1 接口定义（.tars 文件）

```cpp
// AServant.tars
module Test
{
    interface AServant
    {
        // 串行调用接口
        int queryResultSerial(string sIn, out string sOut);
        
        // 并行调用接口
        int queryResultParallel(string sIn, out string sOut);
    };
    
    interface BServant
    {
        int queryResult(string sIn, out string sOut);
    };
    
    interface CServant
    {
        int queryResult(string sIn, out string sOut);
    };
};
```

### 3.2 服务端实现头文件

```cpp
// AServantImp.h
#ifndef _AServantImp_H_
#define _AServantImp_H_

#include "servant/Application.h"
#include "AServant.h"

class AServantImp : public Test::AServant
{
public:
    virtual void initialize();
    virtual void destroy();
    
    // 串行调用：A → B → C → 响应客户端
    virtual tars::Int32 queryResultSerial(
        const std::string& sIn,
        std::string &sOut,
        tars::TarsCurrentPtr current);
    
    // 并行调用：A → (B + C) → 响应客户端
    virtual tars::Int32 queryResultParallel(
        const std::string& sIn,
        std::string &sOut,
        tars::TarsCurrentPtr current);

private:
    Test::BServantPrx _pPrxB;  // B服务代理
    Test::CServantPrx _pPrxC;  // C服务代理
};

#endif
```

---

## 四、串行调用场景

### 4.1 场景说明

A服务接收请求 → 调用B服务 → 调用C服务 → 响应客户端

```
客户端
  ↓ 请求
A服务
  ↓ 异步调用
B服务
  ↓ 响应
A服务
  ↓ 异步调用
C服务
  ↓ 响应
A服务
  ↓ 响应
客户端
```

### 4.2 完整实现代码

```cpp
// AServantImp.cpp

#include "AServantImp.h"
#include "servant/Application.h"
#include "servant/Communicator.h"

using namespace std;
using namespace tars;

//////////////////////////////////////////////////////////////
// 步骤1：定义回调类
//////////////////////////////////////////////////////////////

class BServantCallback : public Test::BServantPrxCallback
{
public:
    BServantCallback(TarsCurrentPtr &current, const tars::Promise<std::string> &promise)
    : _current(current)
    , _promise(promise)
    {}
    
    // 成功回调
    virtual void callback_queryResult(tars::Int32 ret, const std::string &sOut)
    {
        if(ret == 0)
        {
            // ✅ 设置 Promise 的值（触发 Future 的 then）
            _promise.setValue(sOut);
        }
        else
        {
            _promise.setException(tars::copyException("B service error", ret));
        }
    }
    
    // 异常回调
    virtual void callback_queryResult_exception(tars::Int32 ret)
    {
        _promise.setException(tars::copyException("B service exception", ret));
    }

private:
    TarsCurrentPtr _current;
    tars::Promise<std::string> _promise;
};

class CServantCallback : public Test::CServantPrxCallback
{
public:
    CServantCallback(TarsCurrentPtr &current, const tars::Promise<std::string> &promise)
    : _current(current)
    , _promise(promise)
    {}
    
    virtual void callback_queryResult(tars::Int32 ret, const std::string &sOut)
    {
        if(ret == 0)
        {
            _promise.setValue(sOut);
        }
        else
        {
            _promise.setException(tars::copyException("C service error", ret));
        }
    }
    
    virtual void callback_queryResult_exception(tars::Int32 ret)
    {
        _promise.setException(tars::copyException("C service exception", ret));
    }

private:
    TarsCurrentPtr _current;
    tars::Promise<std::string> _promise;
};

//////////////////////////////////////////////////////////////
// 步骤2：封装异步调用，返回 Future
//////////////////////////////////////////////////////////////

tars::Future<std::string> sendBReq(
    Test::BServantPrx prx,
    const std::string& sIn,
    tars::TarsCurrentPtr current)
{
    // 创建 Promise
    tars::Promise<std::string> promise;
    
    // 创建回调（将 Promise 传入）
    Test::BServantPrxCallbackPtr cb = new BServantCallback(current, promise);
    
    // 发起异步调用（立即返回）
    prx->async_queryResult(cb, sIn);
    
    // 返回 Future
    return promise.getFuture();
}

tars::Future<std::string> sendCReq(
    Test::CServantPrx prx,
    const std::string& sIn,
    tars::TarsCurrentPtr current)
{
    tars::Promise<std::string> promise;
    Test::CServantPrxCallbackPtr cb = new CServantCallback(current, promise);
    prx->async_queryResult(cb, sIn);
    return promise.getFuture();
}

//////////////////////////////////////////////////////////////
// 步骤3：处理中间结果并继续调用
//////////////////////////////////////////////////////////////

tars::Future<std::string> handleBRspAndSendCReq(
    Test::CServantPrx prx,
    TarsCurrentPtr current,
    const tars::Future<std::string>& future)
{
    try 
    {
        // 获取B服务的结果
        std::string sResult = future.get();
        
        TLOGDEBUG("B service response: " << sResult << endl);
        
        // ✅ 继续调用C服务（返回新的 Future）
        return sendCReq(prx, sResult, current);
    } 
    catch (exception& e) 
    {
        TLOGERROR("B service exception: " << e.what() << endl);
        
        // 异常时返回包含异常的 Future
        tars::Promise<std::string> promise;
        promise.setException(tars::copyException(e.what(), -1));
        return promise.getFuture();
    }
}

//////////////////////////////////////////////////////////////
// 步骤4：最终响应客户端
//////////////////////////////////////////////////////////////

int handleCRspAndReturnClient(
    TarsCurrentPtr current,
    const tars::Future<std::string>& future)
{
    int ret = 0;
    std::string sResult("");
    
    try 
    {
        // 获取C服务的结果
        sResult = future.get();
        
        TLOGDEBUG("C service response: " << sResult << endl);
    } 
    catch (exception& e) 
    {
        ret = -1;
        sResult = e.what();
        TLOGERROR("C service exception: " << e.what() << endl);
    }
    
    // ✅ 关键：手动响应客户端
    Test::AServant::async_response_queryResultSerial(current, ret, sResult);
    
    return 0;
}

//////////////////////////////////////////////////////////////
// 步骤5：服务端接口实现
//////////////////////////////////////////////////////////////

void AServantImp::initialize()
{
    // 初始化服务代理
    _pPrxB = Application::getCommunicator()->stringToProxy<Test::BServantPrx>(
        "Test.BServer.BServantObj");
    _pPrxC = Application::getCommunicator()->stringToProxy<Test::CServantPrx>(
        "Test.CServer.CServantObj");
}

void AServantImp::destroy()
{
}

tars::Int32 AServantImp::queryResultSerial(
    const std::string& sIn,
    std::string &sOut,
    tars::TarsCurrentPtr current)
{
    TLOGDEBUG("queryResultSerial start, request: " << sIn << endl);
    
    // ✅ 关键步骤1：设置为异步响应
    current->setResponse(false);
    
    // ✅ 关键步骤2：发起第一个异步调用（立即返回）
    tars::Future<std::string> f = sendBReq(_pPrxB, sIn, current);
    
    // ✅ 关键步骤3：链式处理
    // B完成后调用C，C完成后响应客户端
    f.then(tars::Bind(&handleBRspAndSendCReq, _pPrxC, current))
     .then(tars::Bind(&handleCRspAndReturnClient, current));
    
    // ✅ 关键步骤4：立即返回，不阻塞线程
    TLOGDEBUG("queryResultSerial return immediately" << endl);
    return 0;
}
```

### 4.3 执行流程分析

```
时间轴：
T0: 客户端发起请求
T1: queryResultSerial() 被调用
    - current->setResponse(false)
    - sendBReq() 发起异步调用
    - return 0 ← 函数立即返回（耗时 < 1ms）
    
T2: 线程被释放，可以处理其他请求
    
... 100ms 后 ...

T100: B服务响应
    - callback_queryResult() 被调用
    - promise.setValue() 触发 Future.then()
    - handleBRspAndSendCReq() 被调用
    - sendCReq() 发起异步调用
    
... 100ms 后 ...

T200: C服务响应
    - callback_queryResult() 被调用
    - promise.setValue() 触发 Future.then()
    - handleCRspAndReturnClient() 被调用
    - async_response_queryResultSerial() 响应客户端
    
T201: 客户端收到响应（总耗时约200ms）
```

**关键点**：
- 服务端线程在 T1 就释放了，可以处理其他请求
- 总耗时 200ms，但线程只占用了 < 1ms
- 线程利用率提升 200 倍以上

---

## 五、并行调用场景

### 5.1 场景说明

A服务接收请求 → 同时调用B和C服务 → 等待都完成 → 响应客户端

```
客户端
  ↓ 请求
A服务
  ├─→ B服务（异步）
  └─→ C服务（异步）
       ↓ 同时响应
A服务（等待所有完成）
  ↓ 响应
客户端
```

### 5.2 完整实现代码

```cpp
//////////////////////////////////////////////////////////////
// 并行调用：处理所有结果并响应客户端
//////////////////////////////////////////////////////////////

int handleBCRspAndReturnClient(
    TarsCurrentPtr current,
    const tars::Future<std::tuple<tars::Future<std::string>, tars::Future<std::string>>>& allFuture)
{
    int ret = 0;
    std::string sResult("");
    
    try 
    {
        // 获取所有 Future 的元组
        const std::tuple<tars::Future<std::string>, tars::Future<std::string>>& tupleFuture = 
            allFuture.get();
        
        // 获取各个结果
        std::string sResult1 = std::get<0>(tupleFuture).get();
        std::string sResult2 = std::get<1>(tupleFuture).get();
        
        TLOGDEBUG("B service response: " << sResult1 << endl);
        TLOGDEBUG("C service response: " << sResult2 << endl);
        
        // 合并结果
        sResult = sResult1 + "|" + sResult2;
    } 
    catch (exception& e) 
    {
        ret = -1;
        sResult = e.what();
        TLOGERROR("Exception: " << e.what() << endl);
    }
    
    // ✅ 响应客户端
    Test::AServant::async_response_queryResultParallel(current, ret, sResult);
    
    return 0;
}

//////////////////////////////////////////////////////////////
// 并行调用接口实现
//////////////////////////////////////////////////////////////

tars::Int32 AServantImp::queryResultParallel(
    const std::string& sIn,
    std::string &sOut,
    tars::TarsCurrentPtr current)
{
    TLOGDEBUG("queryResultParallel start, request: " << sIn << endl);
    
    // ✅ 关键步骤1：设置为异步响应
    current->setResponse(false);
    
    // ✅ 关键步骤2：同时发起两个异步调用
    tars::Future<std::string> f1 = sendBReq(_pPrxB, sIn, current);
    tars::Future<std::string> f2 = sendCReq(_pPrxC, sIn, current);
    
    // ✅ 关键步骤3：使用 WhenAll 等待所有完成
    tars::Future<std::tuple<tars::Future<std::string>, tars::Future<std::string>>> f_all = 
        tars::WhenAll(f1, f2);
    
    // ✅ 关键步骤4：所有完成后响应客户端
    f_all.then(tars::Bind(&handleBCRspAndReturnClient, current));
    
    // ✅ 关键步骤5：立即返回
    TLOGDEBUG("queryResultParallel return immediately" << endl);
    return 0;
}
```

### 5.3 性能对比

**传统串行调用**：
```cpp
// 阻塞调用
_pPrxB->queryResult(sIn, result1);  // 100ms
_pPrxC->queryResult(result1, result2);  // 100ms
// 总耗时：200ms
```

**传统并行调用（多线程）**：
```cpp
// 需要创建线程
std::thread t1([&]() { _pPrxB->queryResult(...); });
std::thread t2([&]() { _pPrxC->queryResult(...); });
t1.join();  // 阻塞等待
t2.join();  // 阻塞等待
// 总耗时：100ms（并行），但需要额外线程开销
```

**异步并行调用**：
```cpp
// 异步调用
tars::Future<std::string> f1 = sendBReq(...);  // < 1ms
tars::Future<std::string> f2 = sendCReq(...);  // < 1ms
tars::WhenAll(f1, f2).then(...);  // < 1ms
return 0;  // 立即返回
// 总耗时：100ms（并行），无线程开销
```

**性能提升**：
- 相比串行：耗时减半（200ms → 100ms）
- 相比多线程：无额外线程开销
- 线程利用率：提升 100 倍以上

---

## 六、关键API说明

### 6.1 `current->setResponse(bool value)`

**作用**：控制是否自动响应客户端

```cpp
// 默认行为（value = true）
tars::Int32 normalMethod(..., tars::TarsCurrentPtr current) {
    // ... 处理逻辑 ...
    return 0;  // ← 函数返回时，框架自动发送响应
}

// 异步响应（value = false）
tars::Int32 asyncMethod(..., tars::TarsCurrentPtr current) {
    current->setResponse(false);  // ← 告诉框架：不要自动响应
    // ... 发起异步调用 ...
    return 0;  // ← 函数返回，但不发送响应
}
```

**重要提示**：
- 必须在函数开始时调用
- 设置为 `false` 后，必须手动响应客户端
- 如果忘记响应，客户端会超时

### 6.2 `async_response_xxx()` 方法

**自动生成**：框架根据 .tars 文件自动生成

```cpp
// .tars 文件定义
interface AServant {
    int queryResult(string sIn, out string sOut);
};

// 自动生成的响应方法
class AServant {
public:
    static void async_response_queryResult(
        tars::TarsCurrentPtr current,  // 请求上下文
        tars::Int32 ret,               // 返回值
        const std::string &sOut        // 输出参数
    );
};
```

**使用方法**：
```cpp
// 在回调中调用
void handleCallback(TarsCurrentPtr current, const std::string& result) {
    // 响应客户端
    AServant::async_response_queryResult(current, 0, result);
}
```

**参数说明**：
- `current`：请求上下文，必须保持有效
- `ret`：返回值（0表示成功，非0表示失败）
- 其他参数：接口定义的输出参数

### 6.3 `TarsCurrentPtr` 生命周期管理

**智能指针**：`TarsCurrentPtr` 是 `TC_AutoPtr<Current>` 的别名

```cpp
// ✅ 正确：保存智能指针
class MyCallback : public SomeServicePrxCallback {
public:
    MyCallback(TarsCurrentPtr current) : _current(current) {}
    
    void callback_xxx(...) {
        // ✅ current 仍然有效
        MyService::async_response_xxx(_current, ret, result);
    }
    
private:
    TarsCurrentPtr _current;  // 智能指针，自动管理生命周期
};

// ❌ 错误：使用裸指针
class BadCallback : public SomeServicePrxCallback {
public:
    BadCallback(Current* current) : _current(current) {}  // ❌ 危险
    
    void callback_xxx(...) {
        // ❌ current 可能已经被释放
        MyService::async_response_xxx(_current, ret, result);
    }
    
private:
    Current* _current;  // ❌ 裸指针，可能悬空
};
```

### 6.4 `tars::Promise` 和 `tars::Future`

**Promise**：用于设置异步结果

```cpp
tars::Promise<std::string> promise;

// 设置成功结果
promise.setValue("success");

// 设置异常
promise.setException(tars::copyException("error", -1));

// 获取 Future
tars::Future<std::string> future = promise.getFuture();
```

**Future**：用于获取异步结果和链式调用

```cpp
tars::Future<std::string> future = ...;

// 链式调用
future.then([](const tars::Future<std::string>& f) {
    std::string result = f.get();
    // 处理结果
    return processResult(result);
}).then([](const tars::Future<std::string>& f) {
    // 继续处理
});

// 检查状态
if (future.isDone()) {
    std::string result = future.get();
}
```

### 6.5 `tars::WhenAll()` 并行等待

**作用**：等待多个 Future 全部完成

```cpp
// 等待2个 Future
tars::Future<std::string> f1 = ...;
tars::Future<std::string> f2 = ...;
auto f_all = tars::WhenAll(f1, f2);

// 等待3个 Future
tars::Future<int> f1 = ...;
tars::Future<std::string> f2 = ...;
tars::Future<double> f3 = ...;
auto f_all = tars::WhenAll(f1, f2, f3);

// 处理结果
f_all.then([](const auto& allFuture) {
    auto tupleFuture = allFuture.get();
    auto result1 = std::get<0>(tupleFuture).get();
    auto result2 = std::get<1>(tupleFuture).get();
    // ...
});
```

---

## 七、执行流程

### 7.1 完整流程图

```
┌─────────────┐
│ 客户端请求   │
└──────┬──────┘
       ↓
┌─────────────────────────────────────────┐
│ 服务端接口函数                           │
│ ┌─────────────────────────────────────┐ │
│ │ current->setResponse(false)         │ │ ← 不自动响应
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ 发起异步调用（立即返回）              │ │ ← 耗时 < 1ms
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ return 0                            │ │ ← 立即返回
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│ 线程立即释放，可处理其他请求              │ ✅ 高并发
└─────────────────────────────────────────┘

       ... 时间流逝（下游服务处理中）...

┌─────────────────────────────────────────┐
│ 异步调用完成                             │
└──────┬──────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│ 回调函数被调用                           │
│ ┌─────────────────────────────────────┐ │
│ │ callback_xxx(ret, result)           │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ promise.setValue(result)            │ │ ← 触发 Future.then()
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│ Future.then() 被调用                     │
│ ┌─────────────────────────────────────┐ │
│ │ 处理结果                             │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ async_response_xxx(current, ...)    │ │ ← 响应客户端
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
       ↓
┌─────────────┐
│ 客户端收到响应│
└─────────────┘
```

### 7.2 时序图（串行调用）

```
客户端    A服务    B服务    C服务
  │        │        │        │
  ├───1──→ │        │        │  客户端发起请求
  │        │        │        │
  │        ├───2──→ │        │  A异步调用B（立即返回）
  │        │        │        │
  │        ← return 0         │  A接口立即返回（不阻塞）
  │        │        │        │
  │        │   ... 100ms ...  │
  │        │        │        │
  │        │ ←──3── │        │  B响应
  │        │        │        │
  │        ├───4────────────→ │  A异步调用C（立即返回）
  │        │        │        │
  │        │   ... 100ms ...  │
  │        │        │        │
  │        │ ←──5────────────┤  C响应
  │        │        │        │
  │ ←──6── │        │        │  A响应客户端
  │        │        │        │
```

**关键时间点**：
- T0: 客户端发起请求
- T1: A接口立即返回（< 1ms）
- T100: B服务响应
- T200: C服务响应，A响应客户端
- 总耗时：200ms
- A服务线程占用：< 1ms（利用率提升 200 倍）

---

## 八、最佳实践

### 8.1 异常处理

**必须处理所有异常**：

```cpp
// ✅ 正确：完整的异常处理
int handleCallback(TarsCurrentPtr current, const tars::Future<std::string>& future) {
    int ret = 0;
    std::string result;
    
    try {
        result = future.get();
    } catch (const tars::TarsException& e) {
        // Tars 框架异常
        ret = e.getErrCode();
        result = e.what();
        TLOGERROR("Tars exception: " << e.what() << endl);
    } catch (const std::exception& e) {
        // 标准异常
        ret = -1;
        result = e.what();
        TLOGERROR("Exception: " << e.what() << endl);
    } catch (...) {
        // 未知异常
        ret = -1;
        result = "Unknown exception";
        TLOGERROR("Unknown exception" << endl);
    }
    
    // ✅ 无论成功还是失败，都要响应客户端
    MyService::async_response_xxx(current, ret, result);
    return 0;
}
```

### 8.2 超时控制

**客户端超时仍然有效**：

```cpp
// 客户端设置超时
prx->tars_timeout(5000);  // 5秒超时

// 服务端处理
tars::Int32 serverMethod(..., tars::TarsCurrentPtr current) {
    current->setResponse(false);
    
    // 如果处理时间 > 5秒，客户端会收到超时错误
    // 但服务端仍应该处理完成并尝试响应
    
    asyncCall().then([current](...) {
        // 即使客户端已超时，仍应响应
        // 框架会自动处理超时的情况
        MyService::async_response_xxx(current, ...);
    });
    
    return 0;
}
```

**建议**：
- 设置合理的客户端超时时间
- 服务端应尽快响应
- 可以在回调中检查是否超时

### 8.3 日志记录

**记录关键节点**：

```cpp
tars::Int32 serverMethod(const std::string& sIn, std::string &sOut, tars::TarsCurrentPtr current) {
    TLOGDEBUG("Request start, input: " << sIn << endl);
    
    current->setResponse(false);
    
    auto future = asyncCall(sIn);
    
    future.then([current, sIn](const tars::Future<std::string>& f) {
        try {
            std::string result = f.get();
            TLOGDEBUG("Request success, input: " << sIn << ", output: " << result << endl);
            MyService::async_response_xxx(current, 0, result);
        } catch (const std::exception& e) {
            TLOGERROR("Request failed, input: " << sIn << ", error: " << e.what() << endl);
            MyService::async_response_xxx(current, -1, e.what());
        }
    });
    
    TLOGDEBUG("Request return immediately" << endl);
    return 0;
}
```

### 8.4 资源管理

**使用智能指针**：

```cpp
// ✅ 正确：使用智能指针
class MyCallback : public SomeServicePrxCallback {
public:
    MyCallback(TarsCurrentPtr current, SomeServicePrx prx)
    : _current(current)
    , _prx(prx)  // ✅ 代理也是智能指针
    {}
    
    void callback_xxx(...) {
        // ✅ 所有资源自动管理
        _prx->anotherCall(...);
        MyService::async_response_xxx(_current, ...);
    }
    
private:
    TarsCurrentPtr _current;
    SomeServicePrx _prx;
};
```

### 8.5 避免阻塞操作

**在回调中避免阻塞**：

```cpp
// ❌ 错误：在回调中阻塞
void callback_xxx(...) {
    // ❌ 不要在回调中执行阻塞操作
    sleep(1);  // 阻塞线程
    
    // ❌ 不要在回调中执行同步RPC调用
    std::string result;
    _prx->syncMethod(input, result);  // 阻塞线程
    
    MyService::async_response_xxx(...);
}

// ✅ 正确：继续使用异步调用
void callback_xxx(...) {
    // ✅ 继续使用异步调用
    _prx->async_method(callback, input);
}
```

---

## 九、常见问题

### 9.1 忘记响应客户端

**问题**：
```cpp
tars::Int32 badMethod(..., tars::TarsCurrentPtr current) {
    current->setResponse(false);
    asyncCall(...);
    return 0;
    // ❌ 忘记在回调中响应客户端
}
```

**现象**：客户端一直等待，直到超时

**解决**：
```cpp
// ✅ 必须在回调中响应
void callback(...) {
    MyService::async_response_xxx(current, ret, result);
}
```

### 9.2 多次响应客户端

**问题**：
```cpp
void callback(...) {
    MyService::async_response_xxx(current, 0, "result1");
    MyService::async_response_xxx(current, 0, "result2");  // ❌ 重复响应
}
```

**现象**：第二次响应会失败，可能导致错误日志

**解决**：
```cpp
// ✅ 只响应一次
void callback(...) {
    if (!_responded) {
        _responded = true;
        MyService::async_response_xxx(current, 0, result);
    }
}
```

### 9.3 Current 对象失效

**问题**：
```cpp
class BadCallback : public SomeServicePrxCallback {
public:
    BadCallback(Current* current) : _current(current) {}  // ❌ 裸指针
    
    void callback_xxx(...) {
        // ❌ current 可能已经被释放
        MyService::async_response_xxx(_current, ...);
    }
    
private:
    Current* _current;  // ❌ 危险
};
```

**解决**：
```cpp
// ✅ 使用智能指针
class GoodCallback : public SomeServicePrxCallback {
public:
    GoodCallback(TarsCurrentPtr current) : _current(current) {}  // ✅ 智能指针
    
    void callback_xxx(...) {
        // ✅ current 仍然有效
        MyService::async_response_xxx(_current, ...);
    }
    
private:
    TarsCurrentPtr _current;  // ✅ 安全
};
```

### 9.4 在回调中执行阻塞操作

**问题**：
```cpp
void callback(...) {
    sleep(1);  // ❌ 阻塞线程
    std::string result;
    _prx->syncMethod(input, result);  // ❌ 同步调用，阻塞线程
    MyService::async_response_xxx(...);
}
```

**影响**：降低并发能力，失去异步响应的优势

**解决**：
```cpp
// ✅ 继续使用异步调用
void callback1(...) {
    _prx->async_method(callback2, input);
}

void callback2(...) {
    MyService::async_response_xxx(...);
}
```

### 9.5 异常未捕获

**问题**：
```cpp
void callback(...) {
    std::string result = future.get();  // ❌ 可能抛出异常
    MyService::async_response_xxx(current, 0, result);
}
```

**现象**：如果 `get()` 抛出异常，客户端不会收到响应

**解决**：
```cpp
// ✅ 捕获所有异常
void callback(...) {
    try {
        std::string result = future.get();
        MyService::async_response_xxx(current, 0, result);
    } catch (...) {
        MyService::async_response_xxx(current, -1, "exception");
    }
}
```

---

## 十、性能对比总结

### 10.1 单次调用性能

| 模式 | 线程占用时间 | 总耗时 | 线程利用率 |
|------|------------|--------|-----------|
| 同步调用 | 100ms | 100ms | 100% |
| 异步响应 | < 1ms | 100ms | < 1% |

**提升**：线程利用率提升 100 倍

### 10.2 串行调用性能

| 模式 | 线程占用时间 | 总耗时 | 线程利用率 |
|------|------------|--------|-----------|
| 同步调用 | 200ms | 200ms | 100% |
| 异步响应 | < 1ms | 200ms | < 0.5% |

**提升**：线程利用率提升 200 倍

### 10.3 并行调用性能

| 模式 | 线程占用时间 | 总耗时 | 额外开销 |
|------|------------|--------|---------|
| 同步串行 | 200ms | 200ms | 无 |
| 多线程并行 | 100ms | 100ms | 线程创建/切换 |
| 异步并行 | < 1ms | 100ms | 无 |

**提升**：
- 相比同步串行：耗时减半
- 相比多线程：无额外开销，线程利用率提升 100 倍

### 10.4 QPS 对比（单线程）

假设每次调用耗时 100ms：

| 模式 | QPS |
|------|-----|
| 同步调用 | 10 |
| 异步响应 | 1000+ |

**提升**：QPS 提升 100 倍以上

---

## 十一、总结

服务端异步响应是 TarsCpp 实现高并发、非阻塞服务的核心技术：

### 核心要点

1. **`current->setResponse(false)`**：告诉框架不要自动响应
2. **异步调用**：使用 `async_xxx` 方法，立即返回
3. **Promise/Future**：管理异步结果和链式调用
4. **手动响应**：在回调中调用 `async_response_xxx`

### 适用场景

- ✅ 需要调用多个下游服务
- ✅ 下游服务响应时间较长
- ✅ 需要高并发处理能力
- ✅ 需要复杂的业务编排

### 性能优势

- 线程利用率提升 100+ 倍
- 单线程 QPS 提升 100+ 倍
- 无额外线程开销
- 支持并行调用

### 最佳实践

- 使用智能指针管理资源
- 完整的异常处理
- 避免在回调中阻塞
- 记录关键日志
- 设置合理超时

通过正确使用服务端异步响应，可以显著提升服务的性能和并发能力！

