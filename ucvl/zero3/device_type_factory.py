class DeviceTypeFactory:
    """
    设备类型工厂类，用于生成设备类型类。
    """
    _device_classes = {}

    @classmethod
    def get_device_class(cls, device_type_id, device_types,json_handler):
        #device_types = json_handler.data["DeviceTypes"]  # 获取设备类型数据
        if device_type_id not in cls._device_classes:
            cls._device_classes[device_type_id] = cls._create_device_class(device_type_id, device_types, json_handler)
        return cls._device_classes[device_type_id]

    @staticmethod
    def _create_device_class(device_type_id, device_types, json_handler):
        # 查找设备类型定义
        device = next((d for d in device_types if d["ID"] == device_type_id), None)
        if not device:
            raise ValueError(f"Device with ID {device_type_id} not found in DeviceTypes")

        # 定义设备类属性
        attributes = {
            'ID': device_type_id,  # 设备类型 ID
            'Name': device["Name"],  # 设备类型名称
            '版本': device["版本"],  # 版本号
            'Tags': {},  # 用于存储设备标签的字典，ID作为键
            'device_infos_handler': json_handler  # 保存JSON处理器
        }

        # 将设备标签（Tag）转为字典，ID为键
        for tag in device["Tags"]:
            tag_id = tag["ID"]
            attributes['Tags'][tag_id] = {
                'ID': tag["ID"],
                'Name': tag["Name"],
                'Type': tag["Type"],
                '起始值': tag["起始值"],
                '实时值': tag["实时值"],
                'RW': tag["RW"]
            }

            # 为每个标签创建 getter 和 setter
            private_attr = f"_{tag['Name']}"

            def create_property(tag_name, tag_id, rw):
                @property
                def prop(self):
                    return getattr(self, private_attr, None)

                @prop.setter
                def prop(self, value):
                    setattr(self, private_attr, value)
                    print(f"正在更新 JSON，tag_name: {tag_name}, real_value: {value}")
                    # 如果 RW 为 'w' 或 'rw'，自动保存到 JSON
                    if rw in ['w', 'rw']:
                        json_handler.update_tag_real_value_by_device_info(self.device_info_id, tag_name=tag_name, real_value=value)

            # 创建动态的属性
            attributes[tag["Name"]] = create_property(tag["Name"], tag_id, tag["RW"])

        # 创建设备类，并返回该类
        device_class = type(device["Name"], (object,), attributes)

        # 初始化方法
        def device_instance_init(self, device_info_id):
            self.device_info_id = device_info_id

        device_class.__init__ = device_instance_init
        return device_class
