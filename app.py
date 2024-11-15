import os
import time
import threading
from ucvl.zero3.mqtt import MQTTClient
import wiringpi
from datetime import datetime
from ucvl.zero3.modbus_rtu import RTU
from ucvl.zero3.json_file import JSONHandler
from ucvl.zero3.device_type_factory import DeviceTypeFactory  # 导入 DeviceTypeFactory

#全局变量------------------------------------------------------------------------------------
#要取的设备类的类型ID
device_type_id = 1  # 本程序我们选择 ID 为 1 的设备类型，流量平衡调节阀
#设备类JSON路径与设备Json路径定义
DEVICE_TYPES_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DeviceTypes.json")  # 设备类型的配置文件
DEVICE_INFOS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DeviceInfos.json")  # 阀门对象的配置文件


# GPIO 引脚配置
PIN_I_UP = 13
PIN_I_DOWN = 16
PIN_Q_REMOTE = 5
PIN_Q_CONN_UP = 7


instances = []  # 用于保存所有实例化的设备对象

previous_b = 0  # 用于记录上一次的 instance.Tags[2000]["实时值"] 值

device_types = JSONHandler(DEVICE_TYPES_FILE_PATH).data["DeviceTypes"]  # 拿到设备类DeviceTypes 的集合

# 初始化MQTT对象
mqtt_client = MQTTClient(broker_ip="192.168.1.15",port=1883,username="admin",password="AJB@123456",instances=instances)
# 初始化 RTU 资源
rtu_resource = RTU(port='/dev/ttyS5', baudrate=9600, timeout=1, parity='N', stopbits=1, bytesize=8)





# 根据设备信息创建设备实例,用device_info初始化device_class创建 的新设备
def create_device_instance(device_info, device_class):

    instance = device_class(device_info.get("ID"))
    instance.ID=device_info.get("ID")
    # 遍历设备信息中的标签，并为实例设置相应的值
    for tag in device_info["Tags"]:

        tag_id = tag["ID"]  # 获取标签的 ID

        if tag_id in instance.Tags:  # 检查标签是否存在于实例的 Tags 字典中

            tag_data = instance.Tags[tag_id]  # 获取标签的数据
            # 设置标签值，优先使用实时值，若实时值为 0，则使用起始值 
            initial_value = tag["实时值"] if tag["实时值"] != 0 else tag["起始值"] 
            tag_data["实时值"]=initial_value

    return instance


# RTU 通信函数
def rtu_communication():
    """
    RTU 通信函数，负责读取和写入设备的实时值。
    """
    global previous_b, instances, rtu_resource
    while True:
        try:
            # 读取操作
            result = rtu_resource.read_holding_registers(DataAddress=0, DataCount=1, SlaveAddress=1)
            if result:
                a = (result[0] / 10000.0) * 100
                for instance in instances:
                    instance.Tags[1000]["实时值"] = a
            else:
                print("读取失败")
        except Exception as e:
            print(f"读取错误：{e}")

        time.sleep(0.2)

        for instance in instances:
            # 只有在 instance.Tags[2000]["实时值"] 值发生变化时才进行写入操作
            if instance.Tags[2000]["实时值"] != previous_b:
                try:
                    converted_b = int((instance.Tags[2000]["实时值"] / 100.0) * 10000)
                    for attempt in range(3):
                        success = rtu_resource.write_holding_registers(SlaveAddress=1, Data=[converted_b], DataAddress=80, DataCount=1)
                        if success:
                            previous_b = instance.Tags[2000]["实时值"]  # 更新 previous_b
                            break
                        else:
                            print(f"写入失败，尝试 {attempt + 1}/3")
                            time.sleep(1)
                except Exception as e:
                    print(f"写入错误：{e}")

        time.sleep(0.2)

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
                if instance.Tags[3000]["实时值"] == 0:
                    current_state_up = wiringpi.digitalRead(PIN_I_UP)
                    current_state_down = wiringpi.digitalRead(PIN_I_DOWN)

                    # 检测上升沿并直接操作 instance.Tags[2000]["实时值"] 的值
                    if current_state_up == 1 and last_state_up == 0:
                        instance.Tags[2000]["实时值"] = min(instance.Tags[2000]["实时值"] + 1, 100)

                    if current_state_down == 1 and last_state_down == 0:
                        instance.Tags[2000]["实时值"] = max(instance.Tags[2000]["实时值"] - 1, 0)

                    last_state_up, last_state_down = current_state_up, current_state_down

            # 检测 instance 的实时值并在引脚上输出
            for instance in instances:
               
                    wiringpi.digitalWrite(PIN_Q_REMOTE, 1 if instance.Tags[3000]["实时值"] == 1 else 0)

               
                    er_value = instance.Tags[7000]["实时值"]
                    wiringpi.digitalWrite(PIN_Q_CONN_UP, 0 if er_value & 1 else 1)  # 检查第0位是否为1

            time.sleep(0.2)
    finally:
        print("清理 GPIO 状态")

# 主函数
def main():
    """
    主函数，负责创建设备类和设备实例。
    """
    global instances,mqtt_client,device_type_id
         # 创建 MQTT 客户端对象


    device_infos_handler=JSONHandler(DEVICE_INFOS_FILE_PATH)
    device_type_id = 1  # 假设我们选择 ID 为 1 的设备类型


    #根据Json文件创建设备类，需要的参数是：哪种类型，
    generated_class = DeviceTypeFactory.get_device_class(device_type_id, device_types,device_infos_handler)


    # 创建实例对象，基于 DeviceInfos 中的设备信息
    for device_info in device_infos_handler.data["DeviceInfos"]:
        if device_info["DevTypeID"] == device_type_id:
            instance = create_device_instance(device_info, generated_class)
            instances.append(instance)

           

    #等待连接成功
    while not mqtt_client.client.is_connected():
        print("等待连接成功...")
        # 在主程序中显式订阅设备类型 1 的主题
        #订阅实例化的设备
        for items in instances:
            mqtt_client.start_publish_loop(device_type_id=1,device_id=items.ID, interval=5)  # 每 5 秒发布设备类型为 1 的设备信息
            mqtt_client.subscribe_device_type(device_type_id=1,device_id=items.ID)

        time.sleep(5)  # 每5秒检查一次连接状态
   
 # 启动线程
def start_threads():
    rtu_thread = threading.Thread(target=rtu_communication)
    gpio_thread = threading.Thread(target=gpio_input_monitor)
  

    rtu_thread.daemon = True
    gpio_thread.daemon = True


    rtu_thread.start()
    gpio_thread.start()



if __name__ == "__main__":
    main()
    start_threads()

    # 无限循环打印状态信息
    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Hello, 【优创未来】, version V0.2.8! 当前时间是 {current_time}")
        
        for instance in instances:
            print(f"阀门开度：{instance.Tags[1000]['实时值']}")
            print(f"阀门给定开度：{instance.Tags[2000]['实时值']}")
            print(f"阀门就地远程状态：{instance.Tags[3000]['实时值']}")
        time.sleep(10)

