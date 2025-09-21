import asyncio
import logging
import time
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
    
    # 标准蓝牙电池服务UUID
    BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
    BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
    
    def __init__(self, heart_rate_callback: Optional[Callable[[int], None]] = None, 
                 battery_callback: Optional[Callable[[int], None]] = None,
                 timeout_callback: Optional[Callable[[], None]] = None):
        self.client: Optional[BleakClient] = None
        self.device_address: Optional[str] = None
        self.device_name: Optional[str] = None
        self.heart_rate_callback = heart_rate_callback
        self.battery_callback = battery_callback
        self.timeout_callback = timeout_callback
        self.is_connected = False
        self.last_heart_rate = 0
        self.last_battery_level = None
        
        # 数据超时检测相关
        self.last_data_time = None
        self.timeout_monitor_task = None
        self.is_monitoring_timeout = False
        
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
            
            # 启动超时监控
            from config import Config
            self.start_timeout_monitoring(Config.DATA_TIMEOUT)
            
            # 检查是否有心率服务和电池服务
            try:
                services = self.client.services
                has_heart_rate_service = False
                has_battery_service = False
                
                service_list = list(services)
                logger.info(f"设备服务列表 (共{len(service_list)}个服务):")
                for service in service_list:
                    logger.info(f"  服务: {service.uuid} - {service.description}")
                    if service.uuid.lower() == self.HEART_RATE_SERVICE_UUID.lower():
                        has_heart_rate_service = True
                        logger.info("  ✓ 发现心率服务")
                    elif service.uuid.lower() == self.BATTERY_SERVICE_UUID.lower():
                        has_battery_service = True
                        logger.info("  ✓ 发现电池服务")
                
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
                
                # 尝试启动电池通知或读取电池电量
                if has_battery_service:
                    await self._start_battery_monitoring()
                else:
                    logger.info("该设备不支持标准电池服务")
                
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
        # 停止超时监控
        self.stop_timeout_monitoring()
        
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
                
                # 更新数据接收时间戳
                self.update_data_timestamp()
                
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
    
    async def _start_battery_monitoring(self):
        """启动电池电量监控"""
        try:
            # 首先尝试读取当前电池电量
            await self._read_battery_level()
            
            # 尝试启动电池电量通知（如果支持）
            try:
                await self.client.start_notify(
                    self.BATTERY_LEVEL_UUID, 
                    self._battery_notification_handler
                )
                logger.info("已启动电池电量通知")
            except Exception as notify_error:
                logger.info(f"电池电量通知不支持，将定期读取: {notify_error}")
                # 如果不支持通知，启动定期读取
                asyncio.create_task(self._periodic_battery_read())
                
        except Exception as e:
            logger.warning(f"启动电池监控失败: {e}")
    
    async def _read_battery_level(self):
        """读取电池电量"""
        try:
            battery_data = await self.client.read_gatt_char(self.BATTERY_LEVEL_UUID)
            if battery_data and len(battery_data) > 0:
                battery_level = battery_data[0]  # 电池电量是0-100的百分比
                self.last_battery_level = battery_level
                logger.debug(f"读取到电池电量: {battery_level}%")
                
                # 调用电池回调函数
                if self.battery_callback:
                    try:
                        self.battery_callback(battery_level)
                    except Exception as e:
                        logger.error(f"电池回调函数执行失败: {e}")
                        
                return battery_level
        except Exception as e:
            logger.debug(f"读取电池电量失败: {e}")
            return None
    
    def _battery_notification_handler(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        """处理电池电量通知"""
        try:
            if data and len(data) > 0:
                battery_level = data[0]  # 电池电量是0-100的百分比
                self.last_battery_level = battery_level
                logger.debug(f"接收到电池电量通知: {battery_level}%")
                
                # 调用电池回调函数
                if self.battery_callback:
                    try:
                        self.battery_callback(battery_level)
                    except Exception as e:
                        logger.error(f"电池回调函数执行失败: {e}")
                        
        except Exception as e:
            logger.error(f"处理电池电量通知失败: {e}")
    
    async def _periodic_battery_read(self):
        """定期读取电池电量（当不支持通知时）"""
        while self.is_connected and self.client and self.client.is_connected:
            try:
                await asyncio.sleep(60)  # 每分钟读取一次
                await self._read_battery_level()
            except Exception as e:
                logger.debug(f"定期电池读取失败: {e}")
                break
    
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
            # 使用缓存的电池电量或尝试读取
            if self.last_battery_level is not None:
                info["battery_level"] = self.last_battery_level
            else:
                # 尝试读取电池电量
                battery_level = await self._read_battery_level()
                info["battery_level"] = battery_level
                
        except Exception as e:
            logger.warning(f"获取设备详细信息失败: {e}")
        
        return info
    
    async def keep_alive(self):
        """保持连接活跃"""
        while True:  # 改为无限循环，不依赖is_connected状态
            try:
                # 如果当前已连接，进行连接检查
                if self.is_connected and self.client:
                    # 每30秒检查一次连接状态
                    await asyncio.sleep(30)
                    
                    # 检查客户端是否存在且连接正常
                    if not self.client:
                        logger.warning("蓝牙客户端不存在")
                        self.is_connected = False
                        continue  # 继续循环等待重连
                    
                    if not self.client.is_connected:
                        logger.warning("设备连接已断开")
                        self.is_connected = False
                        continue  # 继续循环等待重连
                    
                    # 尝试读取设备名称来测试连接
                    await self.client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                    logger.debug("连接状态检查正常")
                else:
                    # 如果未连接，等待一段时间后再检查
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"连接检查失败: {e}")
                self.is_connected = False
                # 不要break，继续循环等待重连
                await asyncio.sleep(5)  # 等待一段时间后继续
    
    def start_timeout_monitoring(self, timeout_seconds: float):
        """启动数据超时监控"""
        if self.is_monitoring_timeout:
            return
            
        self.is_monitoring_timeout = True
        self.last_data_time = time.time()
        self.timeout_monitor_task = asyncio.create_task(self._monitor_data_timeout(timeout_seconds))
        logger.info(f"已启动数据超时监控，超时时间: {timeout_seconds}秒")
    
    def stop_timeout_monitoring(self):
        """停止数据超时监控"""
        self.is_monitoring_timeout = False
        if self.timeout_monitor_task and not self.timeout_monitor_task.done():
            self.timeout_monitor_task.cancel()
            logger.info("已停止数据超时监控")
    
    def update_data_timestamp(self):
        """更新数据接收时间戳"""
        self.last_data_time = time.time()
    
    async def _monitor_data_timeout(self, timeout_seconds: float):
        """监控数据接收超时"""
        try:
            while self.is_monitoring_timeout and self.is_connected:
                await asyncio.sleep(5)  # 每5秒检查一次
                
                if self.last_data_time is None:
                    continue
                
                current_time = time.time()
                time_since_last_data = current_time - self.last_data_time
                
                if time_since_last_data > timeout_seconds:
                    logger.warning(f"数据接收超时: {time_since_last_data:.1f}秒未收到心率数据")
                    
                    # 调用超时回调
                    if self.timeout_callback:
                        try:
                            self.timeout_callback()
                        except Exception as e:
                            logger.error(f"超时回调执行失败: {e}")
                    
                    break
                    
        except asyncio.CancelledError:
            logger.debug("数据超时监控任务已取消")
        except Exception as e:
            logger.error(f"数据超时监控失败: {e}")