class DeviceTypeFactory:
    """
    设备类型工厂类，用于生成设备类型类。
    """
    _device_classes = {}

    @classmethod
    def get_device_class(cls, device_type_id, device_types, device_infos_handler):
        if device_type_id not in cls._device_classes:
            cls._device_classes[device_type_id] = cls._create_device_class(
                device_type_id, device_types, device_infos_handler)
        return cls._device_classes[device_type_id]

    @staticmethod
    def _create_device_class(device_type_id, device_types, device_infos_handler):
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
            'device_infos_handler': device_infos_handler  # 保存JSON处理器
        }

        # 为每个标签创建 getter 和 setter
        for tag in device["Tags"]:
            tag_name = tag["Name"]
            tag_id = tag["ID"]
            private_attr = f"_{tag_name}"

            def create_property(tag_name, tag_id):
                @property
                def prop(self):
                    return getattr(self, private_attr, None)

                @prop.setter
                def prop(self, value):
                    setattr(self, private_attr, value)
                    print(f"正在更新 JSON，tag_name: {tag_name}, real_value: {value}")
                    # 更新实时值到 JSON
                    device_infos_handler.update_tag_real_value_by_device_info(
                        self.ID, tag_name=tag_name, real_value=value
                    )

            # 创建动态的属性
            attributes[tag_name] = create_property(tag_name, tag_id)

        # 创建设备类，并返回该类
        device_class = type(device["Name"], (object,), attributes)

        # 初始化方法
        def device_instance_init(self, device_info_id):
            self.device_info_id = device_info_id

        device_class.__init__ = device_instance_init
        return device_class
