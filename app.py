import os
import time
import threading
from ucvl.zero3.mqtt import MQTTClient
import wiringpi
from datetime import datetime
from ucvl.zero3.modbus_rtu import RTU
from ucvl.zero3.json_file import JSONHandler
from ucvl.zero3.device_type_factory import DeviceTypeFactory  # 导入 DeviceTypeFactory
# 配置文件路径
DEVICE_TYPES_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DeviceTypes.json")  # 设备类型的配置文件
DEVICE_INFOS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DeviceInfos.json")  # 阀门对象的配置文件

# 初始化 JSON 处理器
device_infos_handler = JSONHandler(DEVICE_INFOS_FILE_PATH)  # 初始化 DeviceInfos JSONHandler

# 加载设备类型，只加载一次，常驻内存
device_types_handler = JSONHandler(DEVICE_TYPES_FILE_PATH)  # 初始化 DeviceTypes JSONHandler
device_types_data = device_types_handler.data

device_types = device_types_data["DeviceTypes"]  # 设备类型全局变量，常驻内存

# 初始化全局变量
a = 0.0
previous_b = 0  # 用于记录上一次的 instance.行程给定 值
instances = []  # 用于保存所有实例化的设备对象
instance_info_id_map = {}  # 记录实例化的设备信息 ID 和实例对象的映射关系

# GPIO 引脚配置
PIN_I_UP = 13
PIN_I_DOWN = 16
PIN_Q_REMOTE = 5
PIN_Q_CONN_UP = 7
# 初始化MQTT对象
mqtt_client = MQTTClient(broker_ip="192.168.1.15",port=1883,username="admin",password="AJB@123456",instances=instances)
# 初始化 RTU 资源
rtu_resource = RTU(port='/dev/ttyS5', baudrate=9600, timeout=1, parity='N', stopbits=1, bytesize=8)


# 根据设备信息创建设备实例
def create_device_instance(device_info, device_class):
    """
    根据设备信息创建设备实例。
    :param device_info: 设备信息字典
    :param device_class: 动态生成的设备类
    :return: 设备实例
    """
    device_info_id = device_info.get("ID")  # 根据设备信息提取 device_info_id
    instance = device_class(device_info_id)
    for tag in device_info["Tags"]:
        if hasattr(instance, tag["Name"]):
            # 在初始化阶段禁用自动写入 JSON，以避免在对象未完全初始化时触发写入操作
            setattr(instance, tag["Name"], tag["实时值"] if tag["实时值"] != 0 else tag["起始值"])
    return instance

# RTU 通信函数
def rtu_communication():
    """
    RTU 通信函数，负责读取和写入设备的实时值。
    """
    global a, previous_b, instances, rtu_resource
    while True:
        try:
            # 读取操作
            result = rtu_resource.read_holding_registers(DataAddress=0, DataCount=1, SlaveAddress=1)
            if result:
                a = (result[0] / 10000.0) * 100
                for instance in instances:
                    if hasattr(instance, '行程反馈'):
                        instance.行程反馈 = a
            else:
                print("读取失败")
        except Exception as e:
            print(f"读取错误：{e}")

        time.sleep(0.1)

        for instance in instances:
            # 只有在 instance.行程给定 值发生变化时才进行写入操作
            if instance.行程给定 != previous_b:
                try:
                    converted_b = int((instance.行程给定 / 100.0) * 10000)
                    for attempt in range(3):
                        success = rtu_resource.write_holding_registers(SlaveAddress=1, Data=[converted_b], DataAddress=80, DataCount=1)
                        if success:
                            previous_b = instance.行程给定  # 更新 previous_b
                            break
                        else:
                            print(f"写入失败，尝试 {attempt + 1}/3")
                            time.sleep(1)
                except Exception as e:
                    print(f"写入错误：{e}")

        time.sleep(0.1)

def gpio_input_monitor():
    """
    GPIO 输入监控函数，负责检测输入引脚的状态并对设备实例进行相应操作。
    """
    global instances
    wiringpi.wiringPiSetup()  # 初始化 wiringPi 库

    # 配置引脚模式
    wiringpi.pinMode(PIN_I_UP, wiringpi.INPUT)
    wiringpi.pullUpDnControl(PIN_I_UP, wiringpi.PUD_DOWN)  # 启用下拉电阻

    wiringpi.pinMode(PIN_I_DOWN, wiringpi.INPUT)
    wiringpi.pullUpDnControl(PIN_I_DOWN, wiringpi.PUD_DOWN)  # 启用下拉电阻

    wiringpi.pinMode(PIN_Q_REMOTE, wiringpi.OUTPUT)  # 设置引脚为输出
    wiringpi.pinMode(PIN_Q_CONN_UP, wiringpi.OUTPUT)  # 设置引脚为输出

    last_state_up = wiringpi.digitalRead(PIN_I_UP)
    last_state_down = wiringpi.digitalRead(PIN_I_DOWN)

    try:
        while True:
            for instance in instances:
                if hasattr(instance, '远程') and instance.远程 == 0:
                    current_state_up = wiringpi.digitalRead(PIN_I_UP)
                    current_state_down = wiringpi.digitalRead(PIN_I_DOWN)

                    # 检测上升沿并直接操作 instance.行程给定 的值
                    if current_state_up == 1 and last_state_up == 0:
                        instance.行程给定 = min(instance.行程给定 + 1, 100)

                    if current_state_down == 1 and last_state_down == 0:
                        instance.行程给定 = max(instance.行程给定 - 1, 0)

                    last_state_up, last_state_down = current_state_up, current_state_down

            # 检测 instance 的实时值并在引脚上输出
            for instance in instances:
                if hasattr(instance, '远程'):
                    wiringpi.digitalWrite(PIN_Q_REMOTE, 1 if instance.远程 == 1 else 0)

                if hasattr(instance, 'ER'):
                    er_value = instance.ER
                    wiringpi.digitalWrite(PIN_Q_CONN_UP, 0 if er_value & 1 else 1)  # 检查第0位是否为1

            time.sleep(0.2)
    finally:
        print("清理 GPIO 状态")

# 主函数
def main():
    """
    主函数，负责创建设备类和设备实例。
    """
    global instances, instance_info_id_map,mqtt_client
         # 创建 MQTT 客户端对象
   
    device_type_id = 1  # 假设我们选择 ID 为 1 的设备类型
    generated_class = DeviceTypeFactory.get_device_class(device_type_id, device_types, device_infos_handler, instance_info_id_map)

    # 创建实例对象，基于 DeviceInfos 中的设备信息
    for device_info in device_infos_handler.data["DeviceInfos"]:
        if device_info["DevTypeID"] == device_type_id:
            instance = create_device_instance(device_info, generated_class)
            instances.append(instance)
            instance_info_id_map[id(instance)] = device_info["ID"]  # 使用 id(instance) 作为键
# 定时用MQTT设备信息
def mqtt_publish_loop():
    while True:
        mqtt_client.publish_all_devices_info(instances,device_types)  # 发布所有设备信息
        time.sleep(5)  # 每 5 秒发送一次
 # 启动线程       
def start_threads():
    rtu_thread = threading.Thread(target=rtu_communication)
    gpio_thread = threading.Thread(target=gpio_input_monitor)
    mqtt_publish_thread = threading.Thread(target=mqtt_publish_loop)

    rtu_thread.daemon = True
    gpio_thread.daemon = True
    mqtt_publish_thread.daemon = True

    rtu_thread.start()
    gpio_thread.start()
    mqtt_publish_thread.start()


if __name__ == "__main__":
    main()
    start_threads()

    # 无限循环打印状态信息
    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Hello, 优创未来, version V0.1.100! 当前时间是 {current_time}")
        for instance in instances:
            print(f"阀门开度：{instance.行程反馈}")
            print(f"阀门给定开度：{instance.行程给定}")
            print(f"阀门就地远程状态：{instance.远程}")
        time.sleep(2)

