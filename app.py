import os
import time
import threading
import wiringpi
from datetime import datetime
from ucvl.zero3.modbus_rtu import RTU
from ucvl.zero3.json_file  import JSONHandler

# 初始化全局变量
a = 0.0

previous_b = 0  # 用于记录上一次的 instance.行程给定['实时值'] 值
instance = None
pin_i_up = 13
pin_i_down = 16
pin_q_remote = 5
pin_q_conn_up = 7
json_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DeviceTypes.json")  # 阀门对象的配置文件
json_handler = JSONHandler(json_file_path)  # 初始化 JSONHandler

# 初始化 RTU 资源
rtu_resource = RTU(port='/dev/ttyS5', baudrate=9600, timeout=1, parity='N', stopbits=1, bytesize=8)

# 从设备信息创建类
def create_class_from_device(device):
    attributes = {}
    for tag in device["Tags"]:
        if tag["RW"] == "rw" and tag["实时值"] != 0:
            attributes[tag["Name"]] = {
                "ID": tag["ID"],
                "Type": tag["Type"],
                "RW": tag["RW"],
                "起始值": tag["起始值"],
                "实时值": tag["实时值"]  # 用 JSON 中的实时值
            }
        else:
            attributes[tag["Name"]] = {
                "ID": tag["ID"],
                "Type": tag["Type"],
                "RW": tag["RW"],
                "起始值": tag["起始值"],
                "实时值": tag["起始值"]  # 用起始值进行初始化
            }
    generated_class = type(device["Name"], (object,), attributes)
    return generated_class

# RTU 通信函数
def rtu_communication():
    global a, previous_b, instance, rtu_resource, json_handler
    while True:
        try:
            # 读取操作
            result = rtu_resource.read_holding_registers(DataAddress=0, DataCount=1, SlaveAddress=1)
            if result:
                a = (result[0] / 10000.0) * 100
                if instance and hasattr(instance, '行程反馈'):
                    instance.行程反馈["实时值"] = a
            else:
                print("读取失败")
        except Exception as e:
            print(f"读取错误：{e}")

        time.sleep(0.1)

        # 只有在 instance.行程给定['实时值'] 值发生变化时才进行写入操作
        if instance.行程给定['实时值'] != previous_b:
            try:
                converted_b = int((instance.行程给定['实时值'] / 100.0) * 10000)
                for attempt in range(3):
                    success = rtu_resource.write_holding_registers(SlaveAddress=1, Data=[converted_b], DataAddress=80, DataCount=1)
                    if success:
                        json_handler.update_tag_real_value("行程给定", instance.行程给定['实时值']) # 更新 JSON 中的实时值
                        previous_b = instance.行程给定['实时值']  # 更新 previous_b
                        break
                    else:
                        print(f"写入失败，尝试 {attempt + 1}/3")
                        time.sleep(1)
            except Exception as e:
                print(f"写入错误：{e}")

        time.sleep(0.1)

def gpio_input_monitor():
    global  instance, pin_i_up, pin_i_down, pin_q_remote, pin_q_conn_up
    wiringpi.wiringPiSetup()  # 初始化 wiringPi 库

    wiringpi.pinMode(pin_i_up, wiringpi.INPUT)  # 设置引脚 13 为输入
    wiringpi.pullUpDnControl(pin_i_up, wiringpi.PUD_DOWN)  # 启用下拉电阻

    wiringpi.pinMode(pin_i_down, wiringpi.INPUT)  # 设置引脚 16 为输入
    wiringpi.pullUpDnControl(pin_i_down, wiringpi.PUD_DOWN)  # 启用下拉电阻

    wiringpi.pinMode(pin_q_remote, wiringpi.OUTPUT)  # 设置引脚 pin_q_remote 为输出
    wiringpi.pinMode(pin_q_conn_up, wiringpi.OUTPUT)  # 设置引脚 pin_q_conn_up 为输出

    last_state_up = wiringpi.digitalRead(pin_i_up)
    last_state_down = wiringpi.digitalRead(pin_i_down)

    try:
        while True:
            if instance and hasattr(instance, '远程') and instance.远程["实时值"] == 0:
                current_state_up = wiringpi.digitalRead(pin_i_up)
                current_state_down = wiringpi.digitalRead(pin_i_down)

                # 检测上升沿并直接操作 instance.行程给定['实时值'] 的值
                if current_state_up == 1 and last_state_up == 0:
                    instance.行程给定['实时值'] = min(instance.行程给定['实时值'] + 1, 100)

                if current_state_down == 1 and last_state_down == 0:
                    instance.行程给定['实时值'] = max(instance.行程给定['实时值'] - 1, 0)

                last_state_up, last_state_down = current_state_up, current_state_down

            # 检测 instance 的实时值并在 pin_q_remote 上输出
            if instance and hasattr(instance, '远程'):
                if instance.远程["实时值"] == 1:
                    wiringpi.digitalWrite(pin_q_remote, 1)
                else:
                    wiringpi.digitalWrite(pin_q_remote, 0)

            # 检测 instance 的 ER 实时值的第0位并在 pin_q_conn_up 上输出
            if instance and hasattr(instance, 'ER'):
                er_value = instance.ER["实时值"]
                if er_value & 1:  # 检查第0位是否为1
                    wiringpi.digitalWrite(pin_q_conn_up, 0)
                else:
                    wiringpi.digitalWrite(pin_q_conn_up, 1)

            time.sleep(0.2)
    finally:
        print("清理 GPIO 状态")

# 启动线程
rtu_thread = threading.Thread(target=rtu_communication)
rtu_thread.start()

gpio_thread = threading.Thread(target=gpio_input_monitor)
gpio_thread.start()

# 主函数
def main():
    global instance, json_handler
    json_handler = JSONHandler(json_file_path)  # 将路径传递给类进行初始化
    data = json_handler.data
    generated_class = create_class_from_device(data["DeviceTypes"][0])

    instance = generated_class()
 

if __name__ == "__main__":
    main()

# 无限循环
while True:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Hello, 优创未来, version V0.1.74! 当前时间是 {current_time}")
    print(f"阀门开度：{instance.行程反馈['实时值']}")
    print(f"阀门给定开度：{instance.行程给定['实时值']}")
    print(f"阀门就地远程状态：{instance.远程['实时值']}")
    time.sleep(2)
