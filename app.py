import time
from ucvl.zero3.modbus_rtu import RTU

while True:
    # 然后可以使用RTU类进行操作
    rtu_resource = RTU(
        port='/dev/ttyS5',
        baudrate=9600,
        timeout=1,
        parity='N',
        stopbits=1,
        bytesize=8
        )
    
print(rtu_resource.read_holding_registers(DataAddress=0x00, DataCount=10, SlaveAddress=0x0D))
<<<<<<< HEAD
print("Hello, 世界，第五个版本测试，如果有就是成功!")
=======
print("Hello, 世界，第四fgh 个版本测试，如果有就是成功!")
>>>>>>> b79ba32f8560c892673e83b75f702976e091a141
    
time.sleep(10)
