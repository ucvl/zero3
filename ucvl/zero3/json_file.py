import json
import os

class JSONHandler:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.load_json()

    def load_json(self):
        """加载 JSON 文件内容"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件路径 {self.file_path} 不存在，程序退出。")
        with open(self.file_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_json(self):
        """保存当前数据到 JSON 文件"""
        with open(self.file_path, 'w', encoding='utf-8') as file:
            json.dump(self.data, file, ensure_ascii=False, indent=4)

    def update_tag_real_value(self, device_type_id, tag_name, real_value):
        """
        更新 DeviceTypes 中指定设备类型的标签实时值
        :param device_type_id: 设备类型 ID
        :param tag_name: 需要更新的标签名
        :param real_value: 要更新的实时值
        """
        for device in self.data.get("DeviceTypes", []):
            if device["ID"] == device_type_id:
                for tag in device.get("Tags", []):
                    if tag["Name"] == tag_name:
                        tag["实时值"] = real_value
                        self.save_json()
                        return
        raise ValueError(f"未找到设备类型 ID 为 {device_type_id} 且标签名为 {tag_name} 的条目")

    def get_device(self, device_type_id):
        """
        根据设备类型 ID 获取设备类型信息
        :param device_type_id: 设备类型 ID
        :return: 设备类型信息字典
        """
        for device in self.data.get("DeviceTypes", []):
            if device["ID"] == device_type_id:
                return device
        raise ValueError(f"未找到 ID 为 {device_type_id} 的设备类型")

    def update_tag_real_value_by_device_info(self, device_info_id, tag_name, real_value):
        """
        根据设备信息 ID 更新 DeviceInfos 中的标签实时值
        :param device_info_id: 设备信息的 ID
        :param tag_name: 需要更新的标签名
        :param real_value: 要更新的实时值
        """
        #print(f"准备更新设备信息 ID: {device_info_id}, 标签: {tag_name}, 实时值: {real_value}")
        found_device_info = False
        for device_info in self.data.get("DeviceInfos", []):
            if device_info["ID"] == device_info_id:
                found_device_info = True
                #print(f"找到设备信息: {device_info}")  # 打印找到的设备信息
                found_tag = False
                for tag in device_info.get("Tags", []):
                    if tag["ID"] == tag_name:
                        found_tag = True
                        print(f"找到标签: {tag}")  # 打印找到的标签
                        tag["实时值"] = real_value
                        self.save_json()
                        return
                if not found_tag:
                    print(f"未找到标签名: {tag_name}，当前设备信息中的标签为: {device_info.get('Tags', [])}")
        if not found_device_info:
            print(f"未找到设备信息 ID: {device_info_id}")
        raise ValueError(f"未找到设备信息 ID 为 {device_info_id} 且标签名为 {tag_name} 的条目")


