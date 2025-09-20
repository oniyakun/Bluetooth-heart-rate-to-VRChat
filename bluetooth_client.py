import asyncio
import logging
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
import struct
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class BluetoothHeartRateClient:
    """蓝牙心率设备客户端"""
    
    # 标准蓝牙心率服务UUID
    HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
    HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
    
    def __init__(self, heart_rate_callback: Optional[Callable[[int], None]] = None):
        self.client: Optional[BleakClient] = None
        self.device_address: Optional[str] = None
        self.device_name: Optional[str] = None
        self.heart_rate_callback = heart_rate_callback
        self.is_connected = False
        self.last_heart_rate = 0
        
    async def scan_devices(self, timeout: float = 10.0) -> list:
        """扫描附近的蓝牙心率设备"""
        logger.info(f"开始扫描蓝牙心率设备，超时时间: {timeout}秒")
        
        devices = []
        try:
            # 使用基本的扫描方式
            discovered_devices = await BleakScanner.discover(timeout=timeout)
            
            for device in discovered_devices:
                # 获取设备名称
                device_name = device.name if device.name else "未知设备"
                
                # 记录发现的设备
                logger.info(f"发现{device_name}: {device.address}")
                
                # 检查设备名称是否包含心率相关关键词
                name_keywords = [
                    # 心率相关词汇
                    'heart', 'hr', 'pulse', 'chest', 'strap',
                    # 运动手环/手表品牌
                    'polar', 'garmin', 'wahoo', 'fitbit', 'suunto', 'coros', 'xiaomi', 'huawei', 'samsung',
                    # 设备类型
                    'band', 'watch', 'tracker', 'monitor', 'sensor',
                    # 其他可能的心率设备
                    'mi band', 'smart band', 'fitness', 'sport'
                ]
                has_heart_keyword = any(keyword.lower() in device_name.lower() for keyword in name_keywords)
                
                # 如果设备名称包含心率关键词，或者是未知设备，都加入列表
                if has_heart_keyword or device_name == "未知设备":
                    # 尝试获取RSSI
                    rssi = getattr(device, 'rssi', -999)
                    
                    devices.append({
                        "address": device.address,
                        "name": device_name,
                        "rssi": rssi,
                        "manufacturer_data": {},
                        "service_uuids": []
                    })
                        
        except Exception as e:
            logger.error(f"扫描设备失败: {e}")
            
        logger.info(f"扫描完成，发现 {len(devices)} 个设备")
        return devices
    
    async def connect(self, device_address: str, device_name: str = "未知设备") -> bool:
        """连接到指定的蓝牙设备"""
        try:
            self.device_address = device_address
            self.device_name = device_name
            
            logger.info(f"正在连接到设备: {device_address}")
            
            # 尝试多种连接策略
            connection_strategies = [
                {"timeout": 15.0, "description": "标准连接"},
                {"timeout": 25.0, "description": "延长超时连接"},
                {"timeout": 35.0, "description": "最大超时连接"}
            ]
            
            connected = False
            last_error = None
            
            for i, strategy in enumerate(connection_strategies):
                try:
                    logger.info(f"尝试{strategy['description']} (策略 {i+1}/{len(connection_strategies)})")
                    
                    # 创建新的客户端实例
                    if self.client:
                        try:
                            await self.client.disconnect()
                        except:
                            pass
                    
                    self.client = BleakClient(device_address, timeout=strategy["timeout"])
                    
                    # 尝试连接
                    await self.client.connect()
                    
                    if self.client.is_connected:
                        logger.info(f"✓ {strategy['description']}成功")
                        connected = True
                        break
                        
                except Exception as connect_error:
                    last_error = connect_error
                    logger.warning(f"✗ {strategy['description']}失败: {connect_error}")
                    
                    # 检查是否是GATT服务错误，给出特定提示
                    error_str = str(connect_error).lower()
                    if "gatt" in error_str and ("unreachable" in error_str or "timeout" in error_str):
                        print(f"\n⚠️  连接提示: 设备可能正在被其他设备使用")
                        print("💡 请确保:")
                        print("   • 断开手机与心率设备的连接")
                        print("   • 关闭其他可能连接该设备的应用")
                        print("   • 将设备靠近电脑")
                    
                    # 如果不是最后一次尝试，等待一下再试
                    if i < len(connection_strategies) - 1:
                        await asyncio.sleep(2)
            
            if not connected:
                raise Exception(f"所有连接策略都失败了，最后错误: {last_error}")
            
            if not self.client.is_connected:
                raise Exception("设备连接失败")
            
            self.is_connected = True
            
            # 获取设备信息
            try:
                # 尝试读取设备名称
                device_name_char = "00002a00-0000-1000-8000-00805f9b34fb"  # Device Name Characteristic
                device_name_data = await self.client.read_gatt_char(device_name_char)
                read_device_name = device_name_data.decode('utf-8').strip()
                if read_device_name:
                    self.device_name = read_device_name
                logger.info(f"读取到设备名称: {self.device_name}")
            except Exception as e:
                logger.debug(f"无法读取设备名称: {e}")
            
            # 尝试读取制造商信息
            try:
                manufacturer_char = "00002a29-0000-1000-8000-00805f9b34fb"  # Manufacturer Name String
                manufacturer = await self.client.read_gatt_char(manufacturer_char)
                manufacturer_name = manufacturer.decode('utf-8').strip()
                logger.info(f"制造商: {manufacturer_name}")
                if self.device_name == "未知设备":
                    self.device_name = f"{manufacturer_name} 设备"
            except Exception as e:
                logger.debug(f"无法读取制造商信息: {e}")
            
            # 尝试读取型号信息
            try:
                model_char = "00002a24-0000-1000-8000-00805f9b34fb"  # Model Number String
                model = await self.client.read_gatt_char(model_char)
                model_name = model.decode('utf-8').strip()
                logger.info(f"型号: {model_name}")
                if "未知" in self.device_name:
                    self.device_name = f"{model_name}"
            except Exception as e:
                logger.debug(f"无法读取型号信息: {e}")
            
            logger.info(f"成功连接到设备: {self.device_name} ({device_address})")
            
            # 等待一下让连接稳定
            await asyncio.sleep(1)
            
            # 检查是否有心率服务
            try:
                services = self.client.services
                has_heart_rate_service = False
                
                service_list = list(services)
                logger.info(f"设备服务列表 (共{len(service_list)}个服务):")
                for service in service_list:
                    logger.info(f"  服务: {service.uuid} - {service.description}")
                    if service.uuid.lower() == self.HEART_RATE_SERVICE_UUID.lower():
                        has_heart_rate_service = True
                        logger.info("  ✓ 发现心率服务")
                
                if not has_heart_rate_service:
                    logger.warning("⚠ 该设备不支持标准心率服务")
                    # 检查是否有其他可能的心率相关服务
                    for service in services:
                        for char in service.characteristics:
                            if "heart" in char.description.lower() or "rate" in char.description.lower():
                                logger.info(f"  发现可能的心率特征: {char.uuid} - {char.description}")
                
                # 尝试启动心率通知
                if has_heart_rate_service:
                    await self._start_heart_rate_notifications()
                else:
                    logger.info("跳过心率通知启动，将尝试其他方式获取数据")
                
            except Exception as service_error:
                logger.warning(f"获取服务信息失败: {service_error}")
                logger.info("设备已连接，但无法获取服务信息")
            
            return True
            
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
            self.is_connected = False
            if self.client:
                try:
                    await self.client.disconnect()
                except:
                    pass
                self.client = None
            return False
    
    async def disconnect(self):
        """断开设备连接"""
        if self.client and self.client.is_connected:
            try:
                await self.client.disconnect()
                logger.info(f"已断开设备连接: {self.device_name}")
            except Exception as e:
                logger.error(f"断开连接失败: {e}")
        
        self.is_connected = False
        self.client = None
        self.device_address = None
        self.device_name = None
    
    async def _start_heart_rate_notifications(self):
        """启动心率数据通知"""
        try:
            # 订阅心率测量特征值的通知
            await self.client.start_notify(
                self.HEART_RATE_MEASUREMENT_UUID, 
                self._heart_rate_notification_handler
            )
            logger.info("已启动心率数据通知")
            
        except Exception as e:
            logger.error(f"启动心率通知失败: {e}")
            raise
    
    def _heart_rate_notification_handler(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        """处理心率数据通知"""
        try:
            # 解析心率数据 (根据蓝牙心率服务规范)
            heart_rate = self._parse_heart_rate_data(data)
            
            if heart_rate > 0:
                self.last_heart_rate = heart_rate
                logger.debug(f"接收到心率数据: {heart_rate} bpm")
                
                # 调用回调函数
                if self.heart_rate_callback:
                    try:
                        self.heart_rate_callback(heart_rate)
                    except Exception as e:
                        logger.error(f"心率回调函数执行失败: {e}")
                        
        except Exception as e:
            logger.error(f"处理心率数据失败: {e}")
    
    def _parse_heart_rate_data(self, data: bytearray) -> int:
        """解析心率数据"""
        if len(data) < 2:
            return 0
        
        # 第一个字节包含格式信息
        flags = data[0]
        
        # 检查心率值格式 (bit 0)
        if flags & 0x01:
            # 16位心率值
            if len(data) >= 3:
                heart_rate = struct.unpack('<H', data[1:3])[0]
            else:
                return 0
        else:
            # 8位心率值
            heart_rate = data[1]
        
        return heart_rate
    
    async def get_device_info(self) -> dict:
        """获取设备信息"""
        if not self.client or not self.client.is_connected:
            return {}
        
        info = {
            "address": self.device_address,
            "name": self.device_name,
            "connected": self.is_connected,
            "last_heart_rate": self.last_heart_rate
        }
        
        try:
            # 尝试读取更多设备信息
            services = self.client.services
            service_list = list(services)
            info["services"] = len(service_list)
            
            # 尝试读取电池电量 (如果支持)
            try:
                battery_level = await self.client.read_gatt_char("00002a19-0000-1000-8000-00805f9b34fb")
                info["battery_level"] = battery_level[0] if battery_level else None
            except:
                info["battery_level"] = None
                
        except Exception as e:
            logger.warning(f"获取设备详细信息失败: {e}")
        
        return info
    
    async def keep_alive(self):
        """保持连接活跃"""
        while self.is_connected and self.client and self.client.is_connected:
            try:
                # 每30秒检查一次连接状态
                await asyncio.sleep(30)
                
                # 尝试读取设备名称来测试连接
                if self.client.is_connected:
                    await self.client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                    logger.debug("连接状态检查正常")
                else:
                    logger.warning("设备连接已断开")
                    self.is_connected = False
                    break
                    
            except Exception as e:
                logger.error(f"连接检查失败: {e}")
                self.is_connected = False
                break