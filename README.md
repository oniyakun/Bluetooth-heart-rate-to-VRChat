# 蓝牙心率广播到VRChat OSC转发器

直接从蓝牙心率设备接收数据并转发到VRChat OSC，无需第三方服务。

## 功能特点

- ✅ 支持标准蓝牙心率设备（符合蓝牙心率服务规范）
- ✅ 自动扫描和连接心率设备
- ✅ 实时心率数据转发到VRChat OSC
- ✅ 设备历史记录和自动重连
- ✅ 心率数据平滑处理
- ✅ 完整的配置选项
- ✅ 详细的日志记录

## 系统要求

- Windows 10/11 (支持蓝牙LE)
- Python 3.7+
- 蓝牙适配器
- 标准蓝牙心率设备（如心率带、智能手表等）
- VRChat (启用OSC)

## 安装步骤

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 配置设置（可选）

创建 `.env` 文件或设置环境变量来自定义配置：

```bash
# OSC设置
OSC_IP=127.0.0.1
OSC_PORT=9000

# 蓝牙设置
BLUETOOTH_SCAN_TIMEOUT=10.0
AUTO_CONNECT_LAST_DEVICE=true

# 心率设置
HEART_RATE_MIN=40
HEART_RATE_MAX=200
HEART_RATE_SMOOTHING=true
SMOOTHING_WINDOW_SIZE=5

# 日志设置
LOG_LEVEL=INFO
LOG_TO_FILE=false
```

## 使用方法

### 1. 启动VRChat并启用OSC

确保VRChat中的OSC功能已启用。

### 2. 准备心率设备

- 确保心率设备已开启并处于可发现状态
- 设备应支持标准蓝牙心率服务（大多数现代心率设备都支持）

### 3. 运行程序

```bash
python main.py
```

### 4. 选择设备

程序会自动扫描附近的蓝牙心率设备，选择要连接的设备即可。

## VRChat参数

程序会向VRChat发送以下OSC参数：

### 心率参数
- `/avatar/parameters/Heartrate` (float) - 心率值 (heart_rate/127-1)
- `/avatar/parameters/HeartRateFloat` (float) - 心率值 (heart_rate/127-1)
- `/avatar/parameters/Heartrate2` (float) - 心率值 (heart_rate/255)
- `/avatar/parameters/HeartRateFloat01` (float) - 心率值 (heart_rate/255)
- `/avatar/parameters/Heartrate3` (int) - 原始心率值
- `/avatar/parameters/HeartRateInt` (int) - 原始心率值
- `/avatar/parameters/HeartBeatToggle` (bool) - 心跳切换状态

### 连接状态参数
- `/avatar/parameters/BluetoothHRConnected` (bool) - 蓝牙连接状态
- `/avatar/parameters/BluetoothBattery` (float) - 设备电池电量 (0.0-1.0)

## 配置选项

### 基本设置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `OSC_IP` | 127.0.0.1 | VRChat OSC IP地址 |
| `OSC_PORT` | 9000 | VRChat OSC端口 |
| `BLUETOOTH_SCAN_TIMEOUT` | 10.0 | 蓝牙扫描超时时间（秒） |
| `AUTO_CONNECT_LAST_DEVICE` | true | 自动连接上次使用的设备 |

### 心率处理

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `HEART_RATE_MIN` | 40 | 最小有效心率值 |
| `HEART_RATE_MAX` | 200 | 最大有效心率值 |
| `HEART_RATE_SMOOTHING` | false | 启用心率平滑处理 |
| `SMOOTHING_WINDOW_SIZE` | 5 | 平滑窗口大小 |

### 连接设置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `RECONNECT_ATTEMPTS` | 3 | 重连尝试次数 |
| `RECONNECT_DELAY` | 5.0 | 重连延迟时间（秒） |
| `KEEPALIVE_INTERVAL` | 30.0 | 保活间隔时间（秒） |

### 设备过滤

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEVICE_NAME_FILTER` | "" | 设备名称过滤器 |
| `RSSI_THRESHOLD` | -80 | RSSI信号强度阈值 |

## 支持的设备

理论上支持所有符合蓝牙心率服务规范的设备，包括但不限于：

- Polar心率带系列
- Garmin心率带
- Wahoo心率带
- Apple Watch (需要第三方应用)
- Samsung Galaxy Watch
- Fitbit设备 (部分型号)
- 小米手环 (部分型号)

## 故障排除

### 1. 找不到设备
- 确保设备已开启并处于可发现状态
- 检查设备是否支持标准蓝牙心率服务
- 尝试增加扫描超时时间
- 检查RSSI阈值设置

### 2. 连接失败
- 确保设备未被其他应用占用
- 尝试重启蓝牙适配器
- 检查Windows蓝牙权限设置
- 尝试手动配对设备

### 3. 心率数据不准确
- 启用心率平滑处理
- 调整平滑窗口大小
- 检查设备佩戴是否正确
- 确认设备电池电量充足

### 4. VRChat无法接收数据
- 确认VRChat OSC功能已启用
- 检查OSC IP和端口设置
- 确认防火墙未阻止连接
- 检查VRChat Avatar参数设置

## 日志文件

程序运行时会输出详细的日志信息，可以通过以下方式查看：

- 控制台输出：实时查看程序状态
- 日志文件：设置 `LOG_TO_FILE=true` 保存到文件

## 贡献

欢迎提交Issue和Pull Request来改进这个项目！