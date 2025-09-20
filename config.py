import os
import logging

class Config:
    """配置类 - 蓝牙心率到VRChat OSC"""
    
    # OSC设置
    OSC_IP = os.getenv("OSC_IP", "127.0.0.1")
    OSC_PORT = int(os.getenv("OSC_PORT", "9000"))
    
    # 蓝牙设置
    BLUETOOTH_SCAN_TIMEOUT = float(os.getenv("BLUETOOTH_SCAN_TIMEOUT", "10.0"))
    BLUETOOTH_DEVICE_ADDRESS = os.getenv("BLUETOOTH_DEVICE_ADDRESS", "")  # 可以预设设备地址
    AUTO_CONNECT_LAST_DEVICE = os.getenv("AUTO_CONNECT_LAST_DEVICE", "true").lower() == "true"
    
    # 心率数据设置
    HEART_RATE_MIN = int(os.getenv("HEART_RATE_MIN", "40"))
    HEART_RATE_MAX = int(os.getenv("HEART_RATE_MAX", "200"))
    HEART_RATE_SMOOTHING = os.getenv("HEART_RATE_SMOOTHING", "false").lower() == "true"
    SMOOTHING_WINDOW_SIZE = int(os.getenv("SMOOTHING_WINDOW_SIZE", "5"))
    
    # 连接设置
    RECONNECT_ATTEMPTS = int(os.getenv("RECONNECT_ATTEMPTS", "3"))
    RECONNECT_DELAY = float(os.getenv("RECONNECT_DELAY", "5.0"))
    KEEPALIVE_INTERVAL = float(os.getenv("KEEPALIVE_INTERVAL", "30.0"))
    
    # 日志设置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "bluetooth_heartrate.log")
    
    # 设备过滤设置
    DEVICE_NAME_FILTER = os.getenv("DEVICE_NAME_FILTER", "")  # 可以设置设备名称过滤
    RSSI_THRESHOLD = int(os.getenv("RSSI_THRESHOLD", "-80"))  # RSSI阈值
    
    @classmethod
    def setup_logging(cls):
        """设置日志配置"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # 设置日志级别
        log_level = getattr(logging, cls.LOG_LEVEL, logging.INFO)
        
        # 配置日志处理器
        handlers = [logging.StreamHandler()]
        
        if cls.LOG_TO_FILE:
            handlers.append(logging.FileHandler(cls.LOG_FILE_PATH, encoding='utf-8'))
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=handlers
        )
        
        # 设置第三方库的日志级别
        logging.getLogger("bleak").setLevel(logging.WARNING)
        logging.getLogger("pythonosc").setLevel(logging.WARNING)
    
    @classmethod
    def validate_config(cls):
        """验证配置参数"""
        errors = []
        
        # 验证OSC设置
        if not (1 <= cls.OSC_PORT <= 65535):
            errors.append(f"OSC端口无效: {cls.OSC_PORT}")
        
        # 验证心率范围
        if cls.HEART_RATE_MIN >= cls.HEART_RATE_MAX:
            errors.append(f"心率范围无效: {cls.HEART_RATE_MIN}-{cls.HEART_RATE_MAX}")
        
        # 验证扫描超时
        if cls.BLUETOOTH_SCAN_TIMEOUT <= 0:
            errors.append(f"蓝牙扫描超时无效: {cls.BLUETOOTH_SCAN_TIMEOUT}")
        
        # 验证重连设置
        if cls.RECONNECT_ATTEMPTS < 0:
            errors.append(f"重连次数无效: {cls.RECONNECT_ATTEMPTS}")
        
        if cls.RECONNECT_DELAY < 0:
            errors.append(f"重连延迟无效: {cls.RECONNECT_DELAY}")
        
        # 验证平滑窗口大小
        if cls.SMOOTHING_WINDOW_SIZE <= 0:
            errors.append(f"平滑窗口大小无效: {cls.SMOOTHING_WINDOW_SIZE}")
        
        if errors:
            raise ValueError("配置验证失败:\n" + "\n".join(errors))
    
    @classmethod
    def print_config(cls):
        """打印当前配置"""
        print("=== 蓝牙广播心率到VRChat OSC  ===")
        print(f"OSC地址: {cls.OSC_IP}:{cls.OSC_PORT}")
        print(f"蓝牙扫描超时: {cls.BLUETOOTH_SCAN_TIMEOUT}秒")
        print(f"预设设备地址: {cls.BLUETOOTH_DEVICE_ADDRESS or '未设置'}")
        print(f"自动连接上次设备: {cls.AUTO_CONNECT_LAST_DEVICE}")
        print(f"心率范围: {cls.HEART_RATE_MIN}-{cls.HEART_RATE_MAX} bpm")
        print(f"心率平滑: {cls.HEART_RATE_SMOOTHING}")
        if cls.HEART_RATE_SMOOTHING:
            print(f"平滑窗口大小: {cls.SMOOTHING_WINDOW_SIZE}")
        print(f"重连次数: {cls.RECONNECT_ATTEMPTS}")
        print(f"重连延迟: {cls.RECONNECT_DELAY}秒")
        print(f"保活间隔: {cls.KEEPALIVE_INTERVAL}秒")
        print(f"日志级别: {cls.LOG_LEVEL}")
        print(f"日志文件: {cls.LOG_TO_FILE}")
        if cls.DEVICE_NAME_FILTER:
            print(f"设备名称过滤: {cls.DEVICE_NAME_FILTER}")
        print(f"RSSI阈值: {cls.RSSI_THRESHOLD} dBm")
        print("=" * 40)

# 设备历史记录文件
DEVICE_HISTORY_FILE = "device_history.json"