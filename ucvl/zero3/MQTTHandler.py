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
        self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("MQTT 连接成功")
            # 订阅所有设备的主题
            for instance in self.instances:
                device_type_id = 1  # 假设所有设备类型为 1
                device_info_id = self.instance_info_id_map.get(id(instance))
                topic = f"DeviceType-{device_type_id}-Device-{device_info_id}"
                client.subscribe(topic)
                print(f"订阅主题: {topic}")
        else:
            print(f"MQTT 连接失败，返回代码: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            device_type_id = payload.get("DeviceTypeID")
            devices = payload.get("Devs", [])

            # 遍历所有收到的设备
            for dev in devices:
                device_id = dev.get("ID")
                tags = dev.get("Tags", [])

                # 找到匹配的本地设备实例并更新实时值
                for instance in self.instances:
                    if self.instance_info_id_map.get(id(instance)) == device_id:
                        for tag in tags:
                            tag_id = tag.get("ID")
                            value = tag.get("V")
                            for attr_name in dir(instance):
                                attr = getattr(instance, attr_name, None)
                                if isinstance(attr, dict) and attr.get("ID") == tag_id:
                                    setattr(instance, attr_name, value)
                                    print(f"更新设备 {device_id} 的属性 {attr_name} 为 {value}")
        except Exception as e:
            print(f"处理 MQTT 消息时出错: {e}")

    def publish_device_data(self):
        while True:
            for instance in self.instances:
                device_type_id = 1  # 假设所有设备类型为 1
                device_info_id = self.instance_info_id_map.get(id(instance))
                topic = f"DeviceType-{device_type_id}-Device-{device_info_id}"
                payload = {
                    "DeviceTypeID": device_type_id,
                    "TS": int(time.time()),
                    "Devs": [
                        {
                            "ID": device_info_id,
                            "Tags": [
                                {
                                    "ID": attr.get("ID"),
                                    "V": getattr(instance, attr_name)
                                }
                                for attr_name in dir(instance)
                                if isinstance((attr := getattr(instance, attr_name, None)), dict) and "ID" in attr
                            ]
                        }
                    ]
                }
                self.client.publish(topic, json.dumps(payload))
                print(f"发布数据到主题 {topic}: {payload}")
            time.sleep(5)  # 每 5 秒发布一次数据

    def start(self):
        self.client.connect(self.broker_ip, self.broker_port, 60)
        self.client.loop_start()
        self.publish_device_data()
