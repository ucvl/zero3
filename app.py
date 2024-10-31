import json
import os
import time
import threading
import logging
from datetime import datetime
from ucvl.zero3.modbus_rtu import RTU
import OPi.GPIO as GPIO

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 常量定义
RTU_PORT = '/dev/ttyS5'  # RTU 设备的串口
RTU_BAUDRATE = 9600  # RTU 设备的波特率
GPIO_PIN_1 = 13  # GPIO 输入引脚 1
GPIO_PIN_2 = 16  # GPIO 输入引脚 2
DEVICE_JSON_PATH = os.path.join(os.path.dirname(__file__), "DeviceTypes.json")  # 设备信息 JSON 文件路径

# 自定义异常类
class RTUError(Exception):
    """RTU 相关错误"""
    pass

class GPIOError(Exception):
    """GPIO 相关错误"""
    pass

class Device:
    """设备类，用于表示从 JSON 文件加载的设备信息"""
    def __init__(self, data):
        self.data = {tag["Name"]: {
            "ID": tag["ID"],
            "Type": tag["Type"],
            "RW": tag["RW"],
            "起始值": tag.get("起始值", None),
            "实时值": tag.get("实时值", tag.get("起始值", None))
        } for tag in data["Tags"]}
    
    def update_value(self, name, value):
        """更新设备的实时值"""
        if name in self.data:
            self.data[name]["实时值"] = value

class RTUManager:
    """RTU 通信管理类"""
    def __init__(self, port: str, baudrate: int):
        self.rtu = RTU(port=port, baudrate=baudrate, timeout=1, parity='N', stopbits=1, bytesize=8)
    
    def read_register(self, address: int):
        """读取指定地址的寄存器"""
        try:
            result = self.rtu.read_holding_registers(DataAddress=address, DataCount=1, SlaveAddress=1)
            if result:
                return result[0] / 10000.0 * 100  # 转换为百分比
            else:
                raise RTUError("读取失败")
        except Exception as e:
            raise RTUError(f"读取错误：{e}")

    def write_register(self, address: int, value: float):
        """写入指定地址的寄存器"""
        try:
            converted_value = int((value / 100.0) * 10000)  # 转换为寄存器值
            success = self.rtu.write_holding_registers(SlaveAddress=1, Data=[converted_value], DataAddress=address, DataCount=1)
            if not success:
                raise RTUError("写入失败")
            return True
        except Exception as e:
            raise RTUError(f"写入错误：{e}")

class GPIOManager:
    """GPIO 管理类"""
    def __init__(self):
        GPIO.setmode(GPIO.BOARD)  # 设置 GPIO 引脚编号方式
        self.setup_pins()  # 初始化引脚设置
    
    def setup_pins(self):
        """设置 GPIO 引脚为输入模式"""
        try:
            GPIO.setup(GPIO_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(GPIO_PIN_2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        except Exception as e:
            raise GPIOError(f"GPIO 初始化错误：{e}")

    def monitor_inputs(self):
        """监测 GPIO 输入引脚状态"""
        last_state_1 = GPIO.input(GPIO_PIN_1)  # 记录引脚 1 的上一个状态
        last_state_2 = GPIO.input(GPIO_PIN_2)  # 记录引脚 2 的上一个状态
        while True:
            current_state_1 = GPIO.input(GPIO_PIN_1)  # 读取当前引脚 1 的状态
            current_state_2 = GPIO.input(GPIO_PIN_2)  # 读取当前引脚 2 的状态
            # 检测上升沿并返回变化
            if current_state_1 == GPIO.HIGH and last_state_1 == GPIO.LOW:
                yield 1  # 引脚 1 由低变高，返回 1
            if current_state_2 == GPIO.HIGH and last_state_2 == GPIO.LOW:
                yield -1  # 引脚 2 由低变高，返回 -1
            last_state_1, last_state_2 = current_state_1, current_state_2  # 更新上一个状态
            time.sleep(0.05)  # 每 50 毫秒检测一次

# 主函数
def main():
    """主程序入口"""
    global instance, rtu_manager, gpio_manager
    
    rtu_manager = RTUManager(RTU_PORT, RTU_BAUDRATE)  # 初始化 RTU 管理器
    json_data = load_json(DEVICE_JSON_PATH)  # 加载设备数据
    instance = Device(json_data["DeviceTypes"][0])  # 创建设备实例

    # 启动线程
    threading.Thread(target=rtu_communication, daemon=True).start()  # 启动 RTU 通信线程
    threading.Thread(target=gpio_input_monitor, daemon=True).start()  # 启动 GPIO 输入监测线程

    while True:
        print_status()  # 打印当前状态
        time.sleep(2)  # 每 2 秒打印一次状态

def load_json(file_path: str) -> dict:
    """从指定文件加载 JSON 数据"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)  # 返回解析后的 JSON 数据

def save_json(file_path: str, data: dict):
    """将数据保存为 JSON 格式"""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)  # 保存数据为 JSON 格式

def print_status():
    """打印系统状态信息"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取当前时间
    logging.info(f"Hello, 优创未来, version V0.1.42! 当前时间是 {current_time}")
    logging.info(f"阀门开度：{instance.data['行程反馈']['实时值']}")
    logging.info(f"阀门给定开度：{instance.data['行程给定']['实时值']}")
    logging.info(f"阀门就地远程状态：{instance.data['远程']['实时值']}")

def rtu_communication():
    """处理 RTU 通信"""
    global b, previous_b
    while True:
        try:
            a = rtu_manager.read_register(0)  # 读取值
            instance.update_value("行程反馈", a)  # 更新设备状态
            logging.info(f"读取的百分比值：{a}%")
        except RTUError as e:
            logging.error(e)  # 记录读取错误

        time.sleep(2)  # 每 2 秒读取一次

        # 只有在 b 值发生变化时才进行写入操作
        if b != previous_b:
            try:
                rtu_manager.write_register(80, b)  # 写入值
                previous_b = b  # 更新 previous_b
                save_json(DEVICE_JSON_PATH, {"DeviceTypes": [instance.data]})  # 保存更新后的设备数据
            except RTUError as e:
                logging.error(e)  # 记录写入错误

        time.sleep(2)  # 等待下一次通信

def gpio_input_monitor():
    """监测 GPIO 输入"""
    global b
    gpio_manager = GPIOManager()  # 初始化 GPIO 管理器
    for change in gpio_manager.monitor_inputs():  # 监测输入变化
        b = min(max(b + change, 0), 100)  # 更新 b 的值，限制在 0 到 100 之间
        logging.info(f"阀门就地远程状态：{b}")

if __name__ == "__main__":
    main()  # 启动主程序
