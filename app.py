import json
import os
import time
import threading
from ucvl.zero3.modbus_rtu import RTU

# 初始化全局变量
a = 0.0
b = 0.0
instance = None

# 函数：加载JSON文件
def load_json(file_path):
    """
    读取并解析JSON文件
    :param file_path: JSON文件路径
    :return: 解析后的数据
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

# 函数：保存JSON文件
def save_json(file_path, data):
    """
    保存数据到JSON文件
    :param file_path: JSON文件路径
    :param data: 要保存的数据
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 函数：根据设备信息动态创建类
def create_class_from_device(device):
    """
    根据设备信息动态创建类
    :param device: 设备信息字典
    :return: 动态创建的类
    """
    class_name = device["Name"]
    # 创建属性字典
    attributes = {}
    for tag in device["Tags"]:
        # 将每个Tag的Name作为属性名，其余字段作为属性值存储在字典中
        attr_name = tag["Name"]
        attributes[attr_name] = {
            "ID": tag["ID"],
            "Type": tag["Type"],
            "RW": tag["RW"],
            "起始值": tag.get("起始值", None),
            "实时值": tag.get("实时值", tag.get("起始值", None))
        }
    # 使用type函数动态创建类
    NewClass = type(class_name, (object,), attributes)
    return NewClass

# 函数：RTU通讯
def rtu_communication():
    """
    RTU通讯函数，在独立线程中运行
    """
    global a, b, instance
    json_file_path = os.path.join(os.path.dirname(__file__), "DeviceTypes.json")
    
    while True:
        # 读取寄存器数据
        try:
            result = rtu_resource.read_holding_registers(DataAddress=0, DataCount=1, SlaveAddress=1)
            if result:
                mv_value = result[0]
                a = (mv_value / 10000.0) * 100  # 将0-10000之间的mv信号转换为百分比
                print(f"读取到的百分比值: {a}%")
                # 更新 instance 对象中的实时值
                if instance and hasattr(instance, '行程反馈'):
                    instance.行程反馈["实时值"] = a
            else:
                print("读取数据失败")
        except Exception as e:
            print(f"读取操作出现异常: {e}")
        time.sleep(2)  # 延时以减少频繁操作
        # 写数据操作
        try:
            if instance and hasattr(instance, '行程给定'):
                b = instance.行程给定["实时值"]
                print(f"b--------: {b} ")
            converted_b = int((b / 100.0) * 10000)  # 将0-100的b值转换为0-10000
            success = rtu_resource.write_holding_registers(SlaveAddress=1, Data=[converted_b], DataAddress=50, DataCount=1)
            if success:
                print(f"发送数据成功: {converted_b} 到地址 50")
                # 更新 JSON 文件中的 "行程给定" 的 "起始值"
                data = load_json(json_file_path)
                for tag in data["DeviceTypes"][0]["Tags"]:
                    if tag["Name"] == "行程给定":
                        tag["起始值"] = b
                        break
                save_json(json_file_path, data)
            else:
                print("发送数据失败")
        except Exception as e:
            print(f"写入操作出现异常: {e}")

        time.sleep(2)  # 延时以减少频繁操作

# 初始化RTU资源
rtu_resource = RTU(
    port='/dev/ttyS5',
    baudrate=9600,
    timeout=1,
    parity='N',
    stopbits=1,
    bytesize=8
)

# 创建并启动新线程，运行RTU通讯函数
rtu_thread = threading.Thread(target=rtu_communication)
rtu_thread.start()

# 主函数
def main():
    """
    主函数，加载JSON文件，创建类并初始化实例
    """
    global instance
    # 使用相对路径加载 JSON 文件
    json_file_path = os.path.join(os.path.dirname(__file__), "DeviceTypes.json")
    data = load_json(json_file_path)

    # 只生成一个类
    device = data["DeviceTypes"][0]
    NewClass = create_class_from_device(device)

    # 初始化类实例并访问属性
    instance = NewClass()
    print(f"Created class: {NewClass.__name__}")
    for attr, value in instance.__dict__.items():
        print(f" - {attr}: {value}")

if __name__ == "__main__":
    main()

# 主程序，循环打印信息
while True:
    print("Hello, 世界，第V0.1.22个版本测试!")
    print(f"阀门的实时 开度在main中的显示: {instance.行程反馈['实时值']}")
    time.sleep(10)
