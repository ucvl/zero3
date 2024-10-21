import time
from ucvl.zero3.modbus_rtu import RTU
    # 然后可以使用RTU类进行操作
rtu_resource = RTU(
    port='/dev/ttyS5',
    baudrate=9600,
    timeout=1,
    parity='N',
    stopbits=1,
    bytesize=8
    )
while True:
    print(rtu_resource.read_holding_registers(DataAddress=0x00, DataCount=10, SlaveAddress=0x0D))
    print("Hello, 世界，第7个版本测试!")
    time.sleep(10)
