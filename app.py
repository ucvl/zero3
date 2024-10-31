import json
import os
import time
import threading
from datetime import datetime
from ucvl.zero3.modbus_rtu import RTU
from OPi import GPIO  # 使用 OPi.GPIO 库

# 初始化全局变量
a = 0.0
b = 0.0
previous_b = None  # 用于记录上一次的 b 值
instance = None
# 初始化 RTU 资源
rtu_resource = RTU(port='/dev/ttyS5', baudrate=9600, timeout=1, parity='N', stopbits=1, bytesize=8)
# 加载 JSON 数据
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# 保存 JSON 数据
def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 从设备信息创建类
def create_class_from_device(device):
    attributes = {tag["Name"]: {
        "ID": tag["ID"],
        "Type": tag["Type"],
        "RW": tag["RW"],
        "起始值": tag.get("起始值", None),
        "实时值": tag.get("实时值", tag.get("起始值", None))
    } for tag in device["Tags"]}
    generated_class = type(device["Name"], (object,), attributes)
    return generated_class

# RTU 通信函数
def rtu_communication():
    global a, b, previous_b, instance,rtu_resource
    json_file_path = os.path.join(os.path.dirname(__file__), "DeviceTypes.json")

    while True:
        try:
            # 读取操作
            result = rtu_resource.read_holding_registers(DataAddress=0, DataCount=1, SlaveAddress=1)
            if result:
                a = (result[0] / 10000.0) * 100
                print(f"读取的百分比值：{a}%")
                if instance and hasattr(instance, '行程反馈'):
                    instance.行程反馈["实时值"] = a
            else:
                print("读取失败")
        except Exception as e:
            print(f"读取错误：{e}")

        time.sleep(2)

        # 只有在 b 值发生变化时才进行写入操作
        if b != previous_b:
            try:
                converted_b = int((b / 100.0) * 10000)
                for attempt in range(3):
                    success = rtu_resource.write_holding_registers(SlaveAddress=1, Data=[converted_b], DataAddress=80, DataCount=1)
                    if success:
                        print("写入成功")
                        data = load_json(json_file_path)
                        for tag in data["DeviceTypes"][0]["Tags"]:
                            if tag["Name"] == "行程给定":
                                tag["起始值"] = b
                                break
                        save_json(json_file_path, data)
                        previous_b = b  # 更新 previous_b
                        break
                    else:
                        print(f"写入失败，尝试 {attempt + 1}/3")
                        time.sleep(1)
            except Exception as e:
                print(f"写入错误：{e}")

        time.sleep(2)

# GPIO 输入监测
def gpio_input_monitor():
    global b, instance
    GPIO.setmode(GPIO.BOARD)

    try:
        GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    except Exception as e:
        print(f"GPIO 初始化错误：{e}")
        return  # 退出监测线程

    last_state_13 = GPIO.input(13)
    last_state_16 = GPIO.input(16)

    while True:
        if instance and hasattr(instance, '远程') and instance.远程["实时值"] == 0:
            current_state_13 = GPIO.input(13)
            current_state_16 = GPIO.input(16)

            # 检测上升沿并直接操作 b 的值
            if current_state_13 == 1 and last_state_13 == 0:
                b = min(b + 1, 100)
                print(f"阀门就地远程状态：{b}")
            if current_state_16 == 1 and last_state_16 == 0:
                print(f"阀门就地远程状态：{b}")
                b = max(b - 1, 0)

            last_state_13, last_state_16 = current_state_13, current_state_16
        time.sleep(0.05)



# 启动线程
rtu_thread = threading.Thread(target=rtu_communication)
gpio_thread = threading.Thread(target=gpio_input_monitor)
rtu_thread.start()
gpio_thread.start()

# 主函数
def main():
    global instance
    json_file_path = os.path.join(os.path.dirname(__file__), "DeviceTypes.json")
    data = load_json(json_file_path)
    generated_class = create_class_from_device(data["DeviceTypes"][0])

    instance = generated_class()
    for tag in data["DeviceTypes"][0]["Tags"]:
        if hasattr(instance, tag["Name"]):
            getattr(instance, tag["Name"])["实时值"] = tag.get("实时值", tag.get("起始值", None))

if __name__ == "__main__":
    main()

# 无限循环
while True:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Hello, 优创未来, version V0.1.50! 当前时间是 {current_time}")
    print(f"阀门开度：{instance.行程反馈['实时值']}")
    print(f"阀门给定开度：{instance.行程给定['实时值']}")
    print(f"阀门就地远程状态：{instance.远程['实时值']}")
    time.sleep(2)
