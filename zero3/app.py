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
b = 0.0  # 需要检测的浮点数值
prev_b = 0.0  # 上一个周期的b值

def rtu_communication():
    global a, b, prev_b
    while True:
        # 读取寄存器数据
        result = rtu_resource.read_holding_registers(DataAddress=0, DataCount=1, SlaveAddress=1)
        if result:
            mv_value = result[0]
            a = (mv_value / 10000.0) * 100  # 将0-10000之间的mv信号转换为百分比
            print(f"读取到的百分比值: {a}%")

        # 检测浮点数b的值，如果改变则发送数据
        if b != prev_b:
            success = rtu_resource.write_holding_registers(SlaveAddress=1, Data=[int(a)], DataAddress=50, DataCount=1)
            if success:
                print(f"发送数据成功: {a}% 到地址 50")
            else:
                print("发送数据失败")
            prev_b = b  # 更新上一个周期的b值以反映最新的状态
        else:
            print("b值未改变，不发送数据")

        b = a  # 更新b值为当前周期的a值

        time.sleep(2)

# 创建并启动新线程
rtu_thread = threading.Thread(target=rtu_communication)
rtu_thread.start()

# 主程序
while True:
    print("Hello, 世界，第7个版本测试!")
    time.sleep(10)
