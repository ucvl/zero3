import paho.mqtt.client as mqtt
import json
import time

class MQTTHandler:
    def __init__(self, broker_ip, broker_port, username, password, instances, instance_info_id_map):
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.instances = instances
        self.instance_info_id_map = instance_info_id_map
        self.client = mqtt.Client()
        self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        for instance in self.instances:
            device_type = getattr(instance, "设备类型", "Unknown")
            device_id = self.instance_info_id_map.get(id(instance))
            topic = f"{device_type}-{device_id}"
            client.subscribe(topic)
            print(f"Subscribed to topic: {topic}")

    def on_message(self, client, userdata, msg):
        print(f"Message received from topic {msg.topic}: {msg.payload}")
        try:
            data = json.loads(msg.payload)
            device_type_id = data.get("DeviceTypeID")
            if device_type_id is not None:
                for dev in data["Devs"]:
                    device_id = dev["ID"]
                    instance = next((i for i in self.instances if self.instance_info_id_map[id(i)] == device_id), None)
                    if instance:
                        for tag in dev["Tags"]:
                            tag_id = tag["ID"]
                            value = tag["V"]
                            setattr(instance, f"tag_{tag_id}", value)
                            print(f"Updated device {device_id} tag {tag_id} to {value}")
        except Exception as e:
            print(f"Failed to process incoming message: {e}")

    def publish_device_data(self):
        for instance in self.instances:
            device_type = getattr(instance, "设备类型", "Unknown")
            device_id = self.instance_info_id_map.get(id(instance))
            topic = f"{device_type}-{device_id}"
            timestamp = int(time.time())
            tags = []
            for tag_name, tag_value in instance.__dict__.items():
                if not tag_name.startswith("_"):
                    tags.append({"ID": tag_name, "V": tag_value})
            payload = {
                "DeviceTypeID": 1,
                "TS": timestamp,
                "Devs": [{
                    "ID": device_id,
                    "Tags": tags
                }]
            }
            self.client.publish(topic, json.dumps(payload))
            print(f"Published data to topic {topic}: {payload}")

    def start(self):
        self.client.connect(self.broker_ip, self.broker_port, 60)
        self.client.loop_start()
        while True:
            self.publish_device_data()
            time.sleep(5)