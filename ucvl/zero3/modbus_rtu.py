from pymodbus.client import ModbusSerialClient as ModbusClient

class RTU:
    def __init__(self, port, baudrate, timeout, parity, stopbits, bytesize):
        try:
            self.client = ModbusClient(
                method='rtu',
                port=port,
                baudrate=baudrate, # 这行代码打印文本
                timeout=timeout,
                parity=parity,
                stopbits=stopbits,
                bytesize=bytesize
            )
            if not self.client.connect():
                print("连接失败!")
                self.client = None
        except Exception as e:
            print(f"初始化失败: {e}")
            self.client = None

    def read_holding_registers(self, DataAddress, DataCount, SlaveAddress):
        if self.client:
            try:
                result = self.client.read_holding_registers(address=DataAddress, count=DataCount, unit=SlaveAddress)
                if result.isError():
                    print("读取错误")
                    return None
                return result.registers
            except Exception as e:
                print(f"读取失败: {e}")
                return None
        else:
            print("客户端未初始化")
            return None

    def write_holding_registers(self, SlaveAddress, Data, DataAddress, DataCount):
        if self.client:
            try:
                for i, value in enumerate(Data[:DataCount]):
                    result = self.client.write_register(address=DataAddress + i, value=value, unit=SlaveAddress)
                    if result.isError():
                        print("写入错误")
                        return False
                return True
            except Exception as e:
                print(f"写入失败: {e}")
                return False
        else:
            print("客户端未初始化")
            return False