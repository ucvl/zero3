import paho.mqtt.client as mqtt
import json
import time


class MQTTClient:
    def __init__(self, broker_ip, port, username, password, device_type_id=1):
        self.client = mqtt.Client()
        self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.connect(broker_ip, port, 60)
        self.client.loop_start()
        self.device_type_id = device_type_id  # Set the default DeviceTypeID

    def on_connect(self, client, userdata, flags, rc):
        print(f"MQTT 连接成功, 状态码 {rc}")

    def get_mqtt_topic(self, device_id):
        """
        根据设备ID生成MQTT主题
        """
        return f"AJB1/zero3/{self.device_type_id}/{device_id}"

    def format_device_info(self, instance):
        """
        格式化设备信息为需要发布的数据格式
        """
        tags = [
            {
                'ID': tag_id,
                'V': getattr(instance, tag_name)
            }
            for tag_id, tag_name in enumerate(instance.__dict__, start=1) if not tag_name.startswith('_')
        ]
        
        return {
            'ID': instance.device_info_id,
            'Tags': tags
        }

    def publish_all_devices_info(self, instances):
        """
        发布指定类型设备的状态信息
        """
        # 只发布当前设备类型的所有设备信息
        devices_info = []
        
        for instance in instances:
            if instance.DevTypeID  == self.device_type_id:  # 只发布该设备类型的设备
                devices_info.append(self.format_device_info(instance))
        
        if devices_info:  # 确保有设备信息才发布
            topic = f"AJB1/zero3/{self.device_type_id}"  # 发布到所有设备的主题
            payload = {
                'DeviceTypeID': self.device_type_id,
                'TS': int(time.time()),  # 获取当前时间戳
                'Devs': devices_info  # 所有设备信息放入 Devs 数组
            }

            self.client.publish(topic, json.dumps(payload))
            print(f"发布到 {topic}: {json.dumps(payload)}")

