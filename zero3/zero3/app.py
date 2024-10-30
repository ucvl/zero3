import json
import os
import time
import threading
from ucvl.zero3.modbus_rtu import RTU

# 初始化RTU资源
rtu_resource = RTU(
    port='/dev/ttyS5',
    baudrate=9600,
    timeout=1,
    parity='N',
    stopbits=1,
    bytesize=8
)

a = 0.0  # 用于存储读取的百分比值
b = 0.0  # 外部输入的浮点数值 (0-100)
prev_b = 0.0  # 上一个周期的b值

def load_json(file_path):
    """
    读取并解析JSON文件
    :param file_path: JSON文件路径
    :return: 解析后的数据
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def create_class_from_device(device):
    """
    根据设备信息动态创建类
    :param device: 设备信息字典
    :return: 动态创建的类
    """
    class_name = device["Name"]
    attributes = {tag["Name"]: None for tag in device["Tags"]}
    
    # 使用type函数动态创建类
    NewClass = type(class_name, (object,), attributes)
    return NewClass

def create_classes_from_json(data):
    """
    从JSON数据中创建所有设备类
    :param data: JSON数据
    :return: 创建的类列表
    """
    classes = []
    for device in data["DeviceTypes"]:
        NewClass = create_class_from_device(device)
        classes.append(NewClass)
    return classes

def rtu_communication():
    """
    RTU通讯函数，在独立线程中运行
    """
    global a, b, prev_b
    while True:
        # 读取寄存器数据
        try:
            result = rtu_resource.read_holding_registers(DataAddress=0, DataCount=1, SlaveAddress=1)
            if result:
                mv_value = result[0]
                a = (mv_value / 10000.0) * 100  # 将0-10000之间的mv信号转换为百分比
                print(f"读取到的百分比值: {a}%")
            else:
                print("读取数据失败")
        except Exception as e:
            print(f"读取操作出现异常: {e}")

        # 在读取操作有结果后（无论成功还是失败），才进行写操作
        if b != prev_b:
            try:
                converted_b = int((b / 100.0) * 10000)  # 将0-100的b值转换为0-10000
                success = rtu_resource.write_holding_registers(SlaveAddress=1, Data=[converted_b], DataAddress=50, DataCount=1)
                if success:
                    print(f"发送数据成功: {converted_b} 到地址 50")
                else:
                    print("发送数据失败")
                prev_b = b  # 更新上一个周期的b值以反映最新的状态
            except Exception as e:
                print(f"写入操作出现异常: {e}")
        else:
            print("b值未改变，不发送数据")

        # 延时以减少频繁操作
        time.sleep(2)

# 创建并启动新线程，运行RTU通讯函数
rtu_thread = threading.Thread(target=rtu_communication)
rtu_thread.start()

def main():
    """
    主函数，加载JSON文件，创建类并初始化实例
    """
    # 使用相对路径加载 JSON 文件
    json_file_path = os.path.join(os.path.dirname(__file__), "DeviceTypes.json")
    data = load_json(json_file_path)
    
    classes = create_classes_from_json(data)
    
    # 初始化类实例并访问属性
    for cls in classes:
        instance = cls()
        print(f"Created class: {cls.__name__}")
        for attr in instance.__dict__.keys():
            print(f" - {attr}: {getattr(instance, attr)}")
    
    # 访问特定类（例如，第一个类）
    specific_class = classes[0]
    instance = specific_class()
    print(f"访问特定类: {specific_class.__name__}")
    for attr in instance.__dict__.keys():
        print(f" - {attr}: {getattr(instance, attr)}")

if __name__ == "__main__":
    main()

# 主程序，循环打印信息
while True:
    print("Hello, 世界，第7个版本测试!")
    time.sleep(10)
