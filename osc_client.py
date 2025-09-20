import logging
from pythonosc import udp_client
from config import Config
import threading
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)

class VRChatOSCClient:
    """VRChat OSC客户端 - 蓝牙心率版本"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self.last_heart_rate = 0
        self.keepalive_thread = None
        self.running = False
        self.hb_toggle = False  # 心跳切换状态
        
        # 心率平滑处理
        self.heart_rate_history = deque(maxlen=Config.SMOOTHING_WINDOW_SIZE)
        
    def connect(self):
        """连接到VRChat OSC"""
        try:
            self.client = udp_client.SimpleUDPClient(Config.OSC_IP, Config.OSC_PORT)
            self.connected = True
            self.running = True
            logger.info(f"OSC客户端已连接到 {Config.OSC_IP}:{Config.OSC_PORT}")
            
            # 启动保活线程
            self.start_keepalive()
            return True
            
        except Exception as e:
            logger.error(f"OSC连接失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开OSC连接"""
        self.running = False
        self.connected = False
        
        if self.keepalive_thread and self.keepalive_thread.is_alive():
            self.keepalive_thread.join(timeout=1)
        
        logger.info("OSC客户端已断开")
    
    def send_heart_rate(self, heart_rate: int, battery_level: Optional[int] = None):
        """发送心率数据到VRChat，同时可选发送电池电量"""
        if not self.connected or not self.client:
            logger.warning("OSC未连接，无法发送心率数据")
            return False
        
        # 验证心率范围
        if not (Config.HEART_RATE_MIN <= heart_rate <= Config.HEART_RATE_MAX):
            logger.warning(f"心率值超出范围: {heart_rate} (范围: {Config.HEART_RATE_MIN}-{Config.HEART_RATE_MAX})")
            return False
        
        # 心率平滑处理
        if Config.HEART_RATE_SMOOTHING:
            heart_rate = self._smooth_heart_rate(heart_rate)
        
        try:
            # 完全匹配原版的心率参数
            heartrates = [
                {
                    'address': '/avatar/parameters/Heartrate',
                    'args': {
                        'type': 'f',
                        'value': heart_rate / 127 - 1
                    }
                },
                {
                    'address': "/avatar/parameters/HeartRateFloat",
                    'args': {
                        'type': "f",
                        'value': heart_rate / 127 - 1
                    }
                },
                {
                    'address': "/avatar/parameters/Heartrate2",
                    'args': {
                        'type': "f",
                        'value': heart_rate / 255
                    }
                },
                {
                    'address': "/avatar/parameters/HeartRateFloat01",
                    'args': {
                        'type': "f",
                        'value': heart_rate / 255
                    }
                },
                {
                    'address': "/avatar/parameters/Heartrate3",
                    'args': {
                        'type': "i",
                        'value': heart_rate
                    }
                },
                {
                    'address': "/avatar/parameters/HeartRateInt",
                    'args': {
                        'type': "i",
                        'value': heart_rate
                    }
                },
                {
                    'address': "/avatar/parameters/HeartBeatToggle",
                    'args': {
                        'type': "b",
                        'value': self.hb_toggle
                    }
                }
            ]
            
            # 如果提供了电池电量，添加电池参数
            if battery_level is not None:
                heartrates.append({
                    'address': "/avatar/parameters/BluetoothBattery",
                    'args': {
                        'type': "f",
                        'value': battery_level / 100.0
                    }
                })
            
            # 发送所有心率参数（和电池参数）
            for element in heartrates:
                try:
                    address = element['address']
                    value = element['args']['value']
                    
                    self.client.send_message(address, value)
                    
                    # 心跳切换参数发送后切换状态
                    if address == "/avatar/parameters/HeartBeatToggle":
                        self.hb_toggle = not self.hb_toggle
                        
                except Exception as e:
                    logger.error(f"发送OSC消息失败 {element['address']}: {e}")
            
            self.last_heart_rate = heart_rate
            
            # 记录发送的数据
            if battery_level is not None:
                logger.debug(f"已发送心率和电池数据到VRChat: {heart_rate} bpm, 电量: {battery_level}%")
            else:
                logger.debug(f"已发送心率数据到VRChat: {heart_rate} bpm")
            return True
            
        except Exception as e:
            logger.error(f"发送OSC消息失败: {e}")
            return False
    
    def _smooth_heart_rate(self, heart_rate: int) -> int:
        """心率平滑处理"""
        self.heart_rate_history.append(heart_rate)
        
        if len(self.heart_rate_history) < 2:
            return heart_rate
        
        # 计算移动平均值
        smoothed = sum(self.heart_rate_history) / len(self.heart_rate_history)
        return int(round(smoothed))
    
    def send_keepalive(self):
        """发送保活消息"""
        if not self.connected or not self.client:
            return
        
        try:
            # 发送保活信号 - 使用蓝牙连接状态
            self.client.send_message("/avatar/parameters/BluetoothHRConnected", True)
            logger.debug("已发送OSC保活信号")
        except Exception as e:
            logger.warning(f"发送保活信号失败: {e}")
    
    def start_keepalive(self):
        """启动保活线程"""
        def keepalive_worker():
            while self.running:
                self.send_keepalive()
                time.sleep(Config.KEEPALIVE_INTERVAL)
        
        self.keepalive_thread = threading.Thread(target=keepalive_worker, daemon=True)
        self.keepalive_thread.start()
        logger.info("OSC保活线程已启动")
    
    def send_connection_status(self, connected: bool, device_name: Optional[str] = None):
        """发送蓝牙连接状态"""
        if not self.connected or not self.client:
            return
        
        try:
            self.client.send_message("/avatar/parameters/BluetoothHRConnected", connected)
            
            logger.debug(f"已发送蓝牙连接状态: {connected}")
            if device_name:
                logger.debug(f"设备名称: {device_name}")
                
        except Exception as e:
            logger.warning(f"发送连接状态失败: {e}")
    
    def send_device_info(self, device_info: dict):
        """发送设备信息"""
        if not self.connected or not self.client:
            return
        
        try:
            # 发送电池电量 (如果有)
            if "battery_level" in device_info and device_info["battery_level"] is not None:
                battery_percent = device_info["battery_level"] / 100.0
                self.client.send_message("/avatar/parameters/BluetoothBattery", battery_percent)
                logger.info(f"已发送电池电量到VRChat: {device_info['battery_level']}% -> {battery_percent}")
            else:
                logger.warning(f"设备信息中没有电池电量数据: {device_info}")
            
            logger.debug("已发送设备信息到VRChat")
            
        except Exception as e:
            logger.warning(f"发送设备信息失败: {e}")
    
    def send_custom_parameter(self, parameter: str, value):
        """发送自定义参数"""
        if not self.connected or not self.client:
            logger.warning("OSC未连接，无法发送自定义参数")
            return False
        
        try:
            self.client.send_message(f"/avatar/parameters/{parameter}", value)
            logger.debug(f"已发送自定义参数: {parameter} = {value}")
            return True
        except Exception as e:
            logger.error(f"发送自定义参数失败: {e}")
            return False