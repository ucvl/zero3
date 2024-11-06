import json
import time
import threading
import paho.mqtt.client as mqtt
from datetime import datetime

class MQTTHandler:
    def __init__(self, broker_ip, broker_port, instances, instance_info_id_map):
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.client = mqtt.Client()
        self.instances = instances
        self.instance_info_id_map = instance_info_id_map

        # 绑定回调函数
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        # 订阅所有设备的主题
        device_type_id = 1  # 假设设备类型为 1，可以根据实际情况修改
        topic = f"{device_type_id}-#"
        self.client.subscribe(topic)
        print(f"Subscribed to topic: {topic}")

    def on_message(self, client, userdata, msg):
        print(f"Message received on topic {msg.topic}: {msg.payload}")
        try:
            payload = json.loads(msg.payload)
            device_type_id = payload.get("DeviceTypeID")
            devs = payload.get("Devs", [])

            for dev in devs:
                device_id = dev.get("ID")
                tags = dev.get("Tags", [])
                for instance in self.instances:
                    if self.instance_info_id_map[id(instance)] == device_id:
                        # 更新属性值
                        for tag in tags:
                            tag_id = tag.get("ID")
                            value = tag.get("V")
                            for instance_tag in instance.__dict__.values():
                                if isinstance(instance_tag, dict) and instance_tag.get("ID") == tag_id:
                                    instance_tag["实时值"] = value
                                    print(f"Updated instance {device_id} tag {tag_id} to value {value}")
        except json.JSONDecodeError:
            print("Failed to decode JSON payload")

    def start(self):
        self.client.connect(self.broker_ip, self.broker_port, 60)
        self.client.loop_start()

        # 定时发布设备状态
        while True:
            device_type_id = 1  # 假设设备类型为 1，可以根据实际情况修改
            devs = []
            for instance in self.instances:
                device_id = self.instance_info_id_map[id(instance)]
                tags = []
                for tag_name, tag_data in instance.__dict__.items():
                    if isinstance(tag_data, dict):
                        tags.append({"ID": tag_data["ID"], "V": tag_data["实时值"]})

                devs.append({
                    "ID": device_id,
                    "Tags": tags
                })

            payload = {
                "DeviceTypeID": device_type_id,
                "TS": int(time.time()),
                "Devs": devs
            }
            topic = f"{device_type_id}-all"
            self.client.publish(topic, json.dumps(payload))
            print(f"Published to topic {topic}: {json.dumps(payload, ensure_ascii=False)}")
            time.sleep(10)  # 每 10 秒发布一次
