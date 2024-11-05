import json
import os

class JSONHandler:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.load_json()

    def load_json(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件路径 {self.file_path} 不存在，程序退出。")
        with open(self.file_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_json(self):
        with open(self.file_path, 'w', encoding='utf-8') as file:
            json.dump(self.data, file, ensure_ascii=False, indent=4)

    def update_tag_real_value(self, tag_name, real_value):
        for device in self.data["DeviceTypes"]:
            for tag in device["Tags"]:
                if tag["Name"] == tag_name:
                    tag["实时值"] = real_value
                    self.save_json()
                    return
        raise ValueError(f"未找到名称为 {tag_name} 的标签")

    def get_device(self, device_type_id):
        for device in self.data["DeviceTypes"]:
            if device["ID"] == device_type_id:
                return device
        raise ValueError(f"未找到 ID 为 {device_type_id} 的设备类型")

    def update_tag_real_value_by_device_info(self, device_info_id, tag_name, real_value):
        """
        根据设备信息 ID 更新设备 JSON 中的实时值
        :param device_info_id: 设备信息的 ID
        :param tag_name: 需要更新的标签名
        :param real_value: 要更新的实时值
        """
        for device_info in self.data["DeviceInfos"]:
            if device_info["ID"] == device_info_id:
                for tag in device_info["Tags"]:
                    if tag["Name"] == tag_name:
                        tag["实时值"] = real_value
                        self.save_json()
                        return
        raise ValueError(f"未找到设备信息 ID 为 {device_info_id} 且标签名为 {tag_name} 的条目")
