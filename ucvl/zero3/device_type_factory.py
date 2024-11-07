import threading

class DeviceTypeFactory:
    _device_classes = {}

    @classmethod
    def get_device_class(cls, device_type_id, device_types, json_handler):
        """
        获取设备类（根据设备类型 ID 创建类并返回）。
        """
        if device_type_id not in cls._device_classes:
            cls._device_classes[device_type_id] = cls._create_device_class(device_type_id, device_types, json_handler)
        return cls._device_classes[device_type_id]

    @staticmethod
    def _create_device_class(device_type_id, device_types, json_handler):
        """
        根据设备类型 ID 和设备类型数据创建设备类。
        """
        device = next((d for d in device_types if d["ID"] == device_type_id), None)
        if not device:
            raise ValueError(f"Device with ID {device_type_id} not found in DeviceTypes")

        # 创建设备类的属性
        attributes = {
            'ID': device_type_id,
            'Name': device["Name"],
            'DevTypeID': device_type_id,
            '版本': device["版本"],
            'Tags': {},  # 用于存储标签的字典
            'device_infos_handler': json_handler
        }

        # 处理设备标签
        for tag in device["Tags"]:
            tag_id = tag["ID"]
            attributes['Tags'][tag_id] = {
                'ID': tag["ID"],
                'Name': tag["Name"],
                'Type': tag["Type"],
                '起始值': tag["起始值"],
                '实时值': tag.get("实时值", tag["起始值"]),
                'RW': tag["RW"]
            }

        # 创建设备类并返回
        device_class = type(device["Name"], (object,), attributes)
        device_class.__init__ = DeviceTypeFactory.device_instance_init
        return device_class

    @staticmethod
    def device_instance_init(self, device_info_id):
        """
        初始化设备实例，启动定时保存设备状态的定时器。
        """
        self.device_info_id = device_info_id
        # 启动定时器，每10秒执行一次 auto_save
        threading.Timer(10, DeviceTypeFactory.auto_save, [self, self.device_infos_handler]).start()

    @staticmethod
    def auto_save(device_instance, json_handler):
        """
        自动保存设备实例的标签数据到 JSON。
        """
        for tag_name, tag in device_instance.Tags.items():
            tag_id = tag["ID"]
            try:
                # 更新标签的实时值到数据库或存储系统
                json_handler.update_tag_real_value_by_device_info(device_instance.device_info_id, tag_name=tag_id, real_value=tag["实时值"])
            except ValueError as e:
                print(f"错误: {e}")
        
        # 重新启动定时器，延迟执行
        threading.Timer(10, DeviceTypeFactory.auto_save, [device_instance, json_handler]).start()  # 每10秒调用一次
