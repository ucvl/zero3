import threading

class DeviceTypeFactory:
    _device_classes = {}

    @classmethod
    def get_device_class(cls, device_type_id, device_types, json_handler):
        if device_type_id not in cls._device_classes:
            cls._device_classes[device_type_id] = cls._create_device_class(device_type_id, device_types, json_handler)
        return cls._device_classes[device_type_id]

    @staticmethod
    def _create_device_class(device_type_id, device_types, json_handler):
        device = next((d for d in device_types if d["ID"] == device_type_id), None)
        if not device:
            raise ValueError(f"Device with ID {device_type_id} not found in DeviceTypes")

        attributes = {
            'ID': device_type_id,
            'Name': device["Name"],
            '版本': device["版本"],
            'Tags': {},  # 用于存储标签的字典
            'device_infos_handler': json_handler
        }

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
    def auto_save(device_instance, json_handler):
        for tag_name, tag in device_instance.Tags.items():
            tag_id = tag["ID"]  # 使用标签的 ID 作为 tag_name
            try:
                json_handler.update_tag_real_value_by_device_info(device_instance.device_info_id, tag_name=tag_id, real_value=tag["实时值"])
            except ValueError as e:
                print(f"错误: {e}")
        # 重新启动定时器，延迟执行
        threading.Timer(10, DeviceTypeFactory.auto_save, [device_instance, json_handler]).start()  # 每10秒调用一次

    @staticmethod
    def device_instance_init(self, device_info_id):
        self.device_info_id = device_info_id
        # 启动定时器，在延迟后执行 auto_save
        DeviceTypeFactory.auto_save, [self, self.device_infos_handler]
