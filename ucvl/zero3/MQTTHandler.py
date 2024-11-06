import json
import time
import paho.mqtt.client as mqtt
import threading
from datetime import datetime

class MQTTHandler:
    def __init__(self, broker_ip, broker_port, username, password, instances, instance_info_id_map):
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.instances = instances
        self.instance_info_id_map = instance_info_id_map
        self.client = mqtt.Client()
        self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker_ip, self.broker_port, 60)

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        # 订阅所有设备类型和设备 ID 相关的主题
        for instance in self.instances:
            device_info_id = self.instance_info_id_map[id(instance)]
            topic = f"DeviceType-{instance.__class__.__name__}-{device_info_id}"
            self.client.subscribe(topic)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            device_type_id = payload["DeviceTypeID"]
            for device in payload["Devs"]:
                device_id = device["ID"]
                # 查找匹配的设备实例
                for instance in self.instances:
                    if self.instance_info_id_map[id(instance)] == device_id:
                        # 更新实例的实时值
                        for tag in device["Tags"]:
                            tag_id = tag["ID"]
                            value = tag["V"]
                            for instance_tag in instance.__class__.__dict__:
                                if hasattr(instance, instance_tag) and isinstance(getattr(instance.__class__, instance_tag), property):
                                    if getattr(instance, instance_tag + "_id", None) == tag_id:
                                        setattr(instance, instance_tag, value)
        except json.JSONDecodeError as e:
            print(f"JSON 解码错误: {e}")
        except Exception as e:
            print(f"处理消息时发生错误: {e}")

    def publish_device_data(self):
        while True:
            timestamp = int(time.time())
            payload = {
                "DeviceTypeID": 1,  # 假设只有一种设备类型
                "TS": timestamp,
                "Devs": []
            }
            for instance in self.instances:
                device_info_id = self.instance_info_id_map[id(instance)]
                tags = []
                for tag_name in instance.__class__.__dict__:
                    if isinstance(getattr(instance.__class__, tag_name), property):
                        tag_value = getattr(instance, tag_name)
                        tag_id = getattr(instance, tag_name + "_id", None)
                        if tag_id is not None:
                            tags.append({"ID": tag_id, "V": tag_value})
                payload["Devs"].append({"ID": device_info_id, "Tags": tags})

            topic = f"DeviceType-{payload['DeviceTypeID']}"
            self.client.publish(topic, json.dumps(payload))
            time.sleep(5)  # 每 5 秒发布一次

    def start(self):
        publish_thread = threading.Thread(target=self.publish_device_data)
        publish_thread.daemon = True
        publish_thread.start()
        self.client.loop_forever()
