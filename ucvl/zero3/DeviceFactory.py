class DeviceTypeFactory:
    """
    设备类型工厂类，用于生成设备类型类。
    """
    _device_classes = {}

    @classmethod
    def get_device_class(cls, device_type_id):
        if device_type_id not in cls._device_classes:
            cls._device_classes[device_type_id] = cls._create_device_class(device_type_id)
        return cls._device_classes[device_type_id]

    @staticmethod
    def _create_device_class(device_type_id):
        device = next((d for d in device_types if d["ID"] == device_type_id), None)
        if not device:
            raise ValueError(f"Device with ID {device_type_id} not found in DeviceTypes, device_types: {device_types}")

        attributes = {}
        for tag in device["Tags"]:
            def create_property(tag_name, tag_id):
                private_attr = f"_{tag_name}"

                @property
                def prop(self):
                    return getattr(self, private_attr, None)

                @prop.setter
                def prop(self, value):
                    setattr(self, private_attr, value)
                    print(f"正在更新 JSON，tag_name: {tag_id}, real_value: {value}")
                    device_infos_handler.update_tag_real_value_by_device_info(instance_info_id_map[id(self)], tag_name=tag_name, real_value=value)

                return prop

            attributes[tag["Name"]] = create_property(tag["Name"], tag["ID"])

        return type(device["Name"], (object,), attributes)
