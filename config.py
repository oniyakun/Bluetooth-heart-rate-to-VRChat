import os
import logging

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载当前目录下的 .env 文件
except ImportError:
    # 如果没有安装 python-dotenv，继续使用环境变量
    pass

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
    
    # 数据超时设置
    DATA_TIMEOUT = float(os.getenv("DATA_TIMEOUT", "10.0"))  # 数据接收超时时间（秒）
    ENABLE_AUTO_RECONNECT_ON_TIMEOUT = os.getenv("ENABLE_AUTO_RECONNECT_ON_TIMEOUT", "true").lower() == "true"
    MAX_TIMEOUT_RECONNECT_ATTEMPTS = int(os.getenv("MAX_TIMEOUT_RECONNECT_ATTEMPTS", "5"))
    
    # 日志设置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "bluetooth_heartrate.log")
    
    # 设备过滤设置
    DEVICE_NAME_FILTER = os.getenv("DEVICE_NAME_FILTER", "")  # 可以设置设备名称过滤
    RSSI_THRESHOLD = int(os.getenv("RSSI_THRESHOLD", "-80"))  # RSSI阈值
    
    # Chatbox设置
    ENABLE_CHATBOX = os.getenv("ENABLE_CHATBOX", "false").lower() == "true"  # 是否启用chatbox功能
    CHATBOX_MESSAGE_FORMAT = os.getenv("CHATBOX_MESSAGE_FORMAT", "心率：{heart_rate}")  # chatbox消息格式
    CHATBOX_SEND_INTERVAL = float(os.getenv("CHATBOX_SEND_INTERVAL", "2.0"))  # chatbox发送间隔（秒）

    # Chatbox进度条设置（用于在Chatbox消息中显示心率进度条）
    # 进度条会按 [PROGRESSBAR_MIN, PROGRESSBAR_MAX] 将心率归一化到 [0, 1]
    # 并生成固定长度的条形字符串。
    PROGRESSBAR_ENABLED = os.getenv("PROGRESSBAR_ENABLED", "true").lower() == "true"
    # 进度条行的前缀文字（会包在 [] 中，且建议以冒号结尾，例如："HR:" 或 "心率:"）
    PROGRESSBAR_LABEL = os.getenv("PROGRESSBAR_LABEL", "")
    PROGRESSBAR_MIN = int(os.getenv("PROGRESSBAR_MIN", "50"))
    PROGRESSBAR_MAX = int(os.getenv("PROGRESSBAR_MAX", "150"))
    PROGRESSBAR_LENGTH = int(os.getenv("PROGRESSBAR_LENGTH", "10"))
    # 只取第一个字符，保证“单字符构成”的效果
    PROGRESSBAR_CHAR = (os.getenv("PROGRESSBAR_CHAR", "█") or "█")[:1]
    # 空白部分字符：避免 VRChat Chatbox 吞空格导致进度条显示比例失真
    PROGRESSBAR_EMPTY_CHAR = (os.getenv("PROGRESSBAR_EMPTY_CHAR", "░") or "░")[:1]
    
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
        
        if cls.DATA_TIMEOUT <= 0:
            errors.append(f"数据超时时间无效: {cls.DATA_TIMEOUT}")
        
        if cls.MAX_TIMEOUT_RECONNECT_ATTEMPTS < 0:
            errors.append(f"超时重连次数无效: {cls.MAX_TIMEOUT_RECONNECT_ATTEMPTS}")

        # 验证进度条配置（仅在启用Chatbox且启用进度条时强制要求）
        if cls.ENABLE_CHATBOX and cls.PROGRESSBAR_ENABLED:
            if cls.PROGRESSBAR_MIN >= cls.PROGRESSBAR_MAX:
                errors.append(f"进度条范围无效: {cls.PROGRESSBAR_MIN}-{cls.PROGRESSBAR_MAX}")
            if cls.PROGRESSBAR_LENGTH <= 0:
                errors.append(f"进度条长度无效: {cls.PROGRESSBAR_LENGTH}")
            if not cls.PROGRESSBAR_CHAR:
                errors.append("进度条字符无效: PROGRESSBAR_CHAR 不能为空")
            if not cls.PROGRESSBAR_EMPTY_CHAR:
                errors.append("进度条空白字符无效: PROGRESSBAR_EMPTY_CHAR 不能为空")
        
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
        print(f"数据超时时间: {cls.DATA_TIMEOUT}秒")
        print(f"启用超时自动重连: {cls.ENABLE_AUTO_RECONNECT_ON_TIMEOUT}")
        if cls.ENABLE_AUTO_RECONNECT_ON_TIMEOUT:
            print(f"超时重连最大次数: {cls.MAX_TIMEOUT_RECONNECT_ATTEMPTS}")
        print(f"日志级别: {cls.LOG_LEVEL}")
        print(f"日志文件: {cls.LOG_TO_FILE}")
        if cls.DEVICE_NAME_FILTER:
            print(f"设备名称过滤: {cls.DEVICE_NAME_FILTER}")
        print(f"RSSI阈值: {cls.RSSI_THRESHOLD} dBm")
        if cls.ENABLE_CHATBOX:
            print(
                f"Chatbox进度条范围: {cls.PROGRESSBAR_MIN}-{cls.PROGRESSBAR_MAX} bpm "
                f"| 长度: {cls.PROGRESSBAR_LENGTH} | 字符: {cls.PROGRESSBAR_CHAR}"
            )
        print("=" * 40)

    @classmethod
    def build_progress_bar(cls, value: int) -> str:
        """生成进度条字符串（固定长度：填充字符 + 空白字符补齐）

        说明：
        - value <= PROGRESSBAR_MIN  -> 全空
        - value >= PROGRESSBAR_MAX  -> 全满
        - 中间按线性比例填充
        """
        # 防御：避免除零
        if cls.PROGRESSBAR_MAX <= cls.PROGRESSBAR_MIN:
            return cls.PROGRESSBAR_CHAR * cls.PROGRESSBAR_LENGTH

        # 归一化并截断
        ratio = (value - cls.PROGRESSBAR_MIN) / (cls.PROGRESSBAR_MAX - cls.PROGRESSBAR_MIN)
        ratio = max(0.0, min(1.0, ratio))

        # 使用“向下取整”让条形不会比百分比更“乐观”（避免 35% 显示成 4/10 这种观感）
        filled = int(ratio * cls.PROGRESSBAR_LENGTH)
        filled = max(0, min(cls.PROGRESSBAR_LENGTH, filled))

        # 注意：VRChat Chatbox 会吞掉/折叠空格，导致进度条看起来“偏满”。
        # 因此用可见字符填充空白部分，保证条形长度稳定。
        empty = cls.PROGRESSBAR_LENGTH - filled
        return (cls.PROGRESSBAR_CHAR * filled) + (cls.PROGRESSBAR_EMPTY_CHAR * empty)

    @classmethod
    def build_progress_line(cls, value: int) -> str:
        """生成进度条整行文本：`[label][bar]XX%`

        - label 可为空字符串
        - 百分比按 min/max 线性映射到 0-100，并做截断
        """
        if cls.PROGRESSBAR_MAX <= cls.PROGRESSBAR_MIN:
            ratio = 1.0
        else:
            ratio = (value - cls.PROGRESSBAR_MIN) / (cls.PROGRESSBAR_MAX - cls.PROGRESSBAR_MIN)
            ratio = max(0.0, min(1.0, ratio))

        # 同样向下取整，保证条形与百分比观感一致
        percent = int(ratio * 100)

        bar = cls.build_progress_bar(value)
        return f"{cls.PROGRESSBAR_LABEL}[{bar}]{percent}%"

# 设备历史记录文件
DEVICE_HISTORY_FILE = "device_history.json"