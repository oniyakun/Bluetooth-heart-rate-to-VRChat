#!/usr/bin/env python3
"""
蓝牙心率广播到VRChat OSC转发器
直接从蓝牙心率设备接收数据并转发到VRChat OSC
"""

import asyncio
import logging
import signal
import sys
import json
import os
from typing import Optional
from datetime import datetime

from config import Config, DEVICE_HISTORY_FILE
from bluetooth_client import BluetoothHeartRateClient
from osc_client import VRChatOSCClient

logger = logging.getLogger(__name__)

class BluetoothHeartRateApp:
    """蓝牙心率应用主类"""
    
    def __init__(self):
        self.bluetooth_client = None
        self.osc_client = None
        self.running = False
        self.device_history = self.load_device_history()
        
    def load_device_history(self) -> dict:
        """加载设备历史记录"""
        try:
            if os.path.exists(DEVICE_HISTORY_FILE):
                with open(DEVICE_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载设备历史记录失败: {e}")
        
        return {"last_device": None, "devices": []}
    
    def save_device_history(self):
        """保存设备历史记录"""
        try:
            with open(DEVICE_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.device_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存设备历史记录失败: {e}")
    
    def add_device_to_history(self, device_address: str, device_name: str):
        """添加设备到历史记录"""
        device_info = {
            "address": device_address,
            "name": device_name,
            "last_connected": datetime.now().isoformat()
        }
        
        # 更新最后连接的设备
        self.device_history["last_device"] = device_info
        
        # 添加到设备列表（避免重复）
        devices = self.device_history.get("devices", [])
        existing_device = next((d for d in devices if d["address"] == device_address), None)
        
        if existing_device:
            existing_device.update(device_info)
        else:
            devices.append(device_info)
            # 只保留最近10个设备
            if len(devices) > 10:
                devices.pop(0)
        
        self.device_history["devices"] = devices
        self.save_device_history()
    
    def heart_rate_callback(self, heart_rate: int):
        """心率数据回调函数"""
        # 实时输出心率数据到控制台
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"💓 [{timestamp}] 心率: {heart_rate} bpm")
        
        if self.osc_client and self.osc_client.connected:
            self.osc_client.send_heart_rate(heart_rate)
        else:
            logger.warning(f"OSC未连接，丢失心率数据: {heart_rate} bpm")
    
    async def scan_and_select_device(self) -> Optional[dict]:
        """扫描并选择蓝牙设备"""
        print("\n正在扫描蓝牙心率设备...")
        
        # 创建临时蓝牙客户端用于扫描
        scanner = BluetoothHeartRateClient()
        devices = await scanner.scan_devices(Config.BLUETOOTH_SCAN_TIMEOUT)
        
        if not devices:
            print("未发现任何蓝牙心率设备")
            return None
        
        # 过滤设备（暂时显示所有设备供用户选择）
        filtered_devices = devices
        
        # 可选的RSSI过滤（仅在设置了严格阈值时）
        if Config.RSSI_THRESHOLD > -100:
            rssi_filtered = [d for d in devices if d["rssi"] >= Config.RSSI_THRESHOLD]
            if rssi_filtered:
                filtered_devices = rssi_filtered
        
        # 可选的设备名称过滤
        if Config.DEVICE_NAME_FILTER:
            name_filtered = [d for d in filtered_devices if Config.DEVICE_NAME_FILTER.lower() in d["name"].lower()]
            if name_filtered:
                filtered_devices = name_filtered
        
        if not filtered_devices:
            print("没有符合条件的设备")
            return None
        
        # 显示设备列表
        print(f"\n发现 {len(filtered_devices)} 个蓝牙设备:")
        print("注意: 设备名称可能在连接后才能获取到真实名称")
        print("\n💡 连接提示:")
        print("• 如果连接失败，请确保设备未连接到手机")
        print("• 小米手环等设备通常不需要系统配对")
        print("• 将设备靠近电脑可提高连接成功率")
        print("-" * 80)
        for i, device in enumerate(filtered_devices):
            name = device['name']
            address = device['address']
            
            # 显示制造商信息（如果有）
            manufacturer_info = ""
            if 'manufacturer_data' in device and device['manufacturer_data']:
                manufacturer_info = f" [制造商数据]"
            
            # 显示服务信息（如果有心率服务）
            service_info = ""
            if 'service_uuids' in device and device['service_uuids']:
                heart_rate_uuid = "0000180d-0000-1000-8000-00805f9b34fb"
                if any(heart_rate_uuid in str(uuid).lower() for uuid in device['service_uuids']):
                    service_info = " [❤️心率服务]"
                elif device['service_uuids']:
                    service_info = f" [服务数: {len(device['service_uuids'])}]"
            
            print(f"{i + 1:2d}. {name:<30} ({address}){manufacturer_info}{service_info}")
        print("-" * 80)
        
        # 显示历史设备
        if self.device_history.get("last_device"):
            last_device = self.device_history["last_device"]
            print(f"\n上次连接的设备: {last_device['name']} ({last_device['address']})")
            
            if Config.AUTO_CONNECT_LAST_DEVICE:
                # 检查上次设备是否在当前扫描结果中
                for device in filtered_devices:
                    if device["address"] == last_device["address"]:
                        print(f"自动连接到上次设备: {device['name']}")
                        return device
        
        # 用户选择设备
        while True:
            try:
                choice = input(f"\n请选择设备 (1-{len(filtered_devices)}) 或按 Enter 重新扫描: ").strip()
                
                if not choice:
                    return await self.scan_and_select_device()
                
                index = int(choice) - 1
                if 0 <= index < len(filtered_devices):
                    selected_device = filtered_devices[index]
                    return selected_device
                else:
                    print("无效的选择，请重试")
                    
            except ValueError:
                print("请输入有效的数字")
            except KeyboardInterrupt:
                return None
    
    async def connect_bluetooth_device(self, device_info: dict) -> bool:
        """连接蓝牙设备"""
        device_address = device_info["address"]
        device_name = device_info["name"]
        
        self.bluetooth_client = BluetoothHeartRateClient(self.heart_rate_callback)
        
        for attempt in range(Config.RECONNECT_ATTEMPTS + 1):
            try:
                logger.info(f"尝试连接蓝牙设备 (第{attempt + 1}次): {device_address}")
                
                if await self.bluetooth_client.connect(device_address, device_name):
                    # 连接成功，保存到历史记录
                    device_info = await self.bluetooth_client.get_device_info()
                    self.add_device_to_history(device_address, device_info.get("name", "未知设备"))
                    
                    # 更新OSC连接状态
                    if self.osc_client:
                        self.osc_client.send_connection_status(True, device_info.get("name"))
                        self.osc_client.send_device_info(device_info)
                    
                    logger.info(f"成功连接到设备: {device_info.get('name')} ({device_address})")
                    return True
                
            except Exception as e:
                logger.error(f"连接设备失败 (第{attempt + 1}次): {e}")
            
            if attempt < Config.RECONNECT_ATTEMPTS:
                logger.info(f"等待 {Config.RECONNECT_DELAY} 秒后重试...")
                await asyncio.sleep(Config.RECONNECT_DELAY)
        
        logger.error(f"无法连接到设备: {device_address}")
        
        # 显示故障排除建议
        print(f"\n❌ 连接失败: {device_info['name']} ({device_address})")
        print("\n🔧 故障排除建议:")
        print("1. 确保设备已从手机断开连接")
        print("2. 将设备靠近电脑 (距离1米内)")
        print("3. 重启设备或重置蓝牙连接")
        print("4. 检查设备是否支持蓝牙心率服务")
        print("5. 尝试在Windows设置中手动配对设备")
        print("\n💡 小米手环用户:")
        print("• 在小米运动健康App中暂时断开手环")
        print("• 确保手环电量充足")
        print("• 可以尝试重启手环")
        
        return False
    
    async def setup_osc_client(self) -> bool:
        """设置OSC客户端"""
        self.osc_client = VRChatOSCClient()
        
        if self.osc_client.connect():
            logger.info("OSC客户端连接成功")
            return True
        else:
            logger.error("OSC客户端连接失败")
            return False
    
    async def run(self):
        """运行主程序"""
        self.running = True
        
        try:
            # 设置OSC客户端
            if not await self.setup_osc_client():
                print("OSC连接失败，请检查VRChat是否运行并启用了OSC")
                return
            
            # 选择蓝牙设备
            device_info = None
            
            # 如果配置了预设设备地址，尝试直接连接
            if Config.BLUETOOTH_DEVICE_ADDRESS:
                device_info = {
                    "address": Config.BLUETOOTH_DEVICE_ADDRESS,
                    "name": "预设设备"
                }
                logger.info(f"使用预设设备地址: {Config.BLUETOOTH_DEVICE_ADDRESS}")
            else:
                device_info = await self.scan_and_select_device()
            
            if not device_info:
                print("未选择设备，程序退出")
                return
            
            # 连接蓝牙设备
            if not await self.connect_bluetooth_device(device_info):
                print("蓝牙设备连接失败，程序退出")
                return
            
            print(f"\n✅ 蓝牙心率设备已连接: {self.bluetooth_client.device_name}")
            print(f"✅ VRChat OSC已连接: {Config.OSC_IP}:{Config.OSC_PORT}")
            print("\n开始转发心率数据到VRChat...")
            print("按 Ctrl+C 退出程序\n")
            
            # 启动保活任务
            keepalive_task = asyncio.create_task(self.bluetooth_client.keep_alive())
            
            # 等待程序结束
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass
            
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在退出...")
        except Exception as e:
            logger.error(f"程序运行出错: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        self.running = False
        
        # 断开蓝牙连接
        if self.bluetooth_client:
            await self.bluetooth_client.disconnect()
        
        # 断开OSC连接
        if self.osc_client:
            self.osc_client.send_connection_status(False)
            self.osc_client.disconnect()
        
        logger.info("程序已退出")

def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到退出信号，正在关闭程序...")
    sys.exit(0)

async def main():
    """主函数"""
    # 设置日志
    Config.setup_logging()
    
    # 验证配置
    try:
        Config.validate_config()
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        return
    
    # 打印配置信息
    Config.print_config()
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并运行应用
    app = BluetoothHeartRateApp()
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"程序启动失败: {e}")
        sys.exit(1)