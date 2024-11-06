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

    def publish_device_info(self, instance):
        """
        定时发布设备信息
        """
        topic = f"UN{instance.device_info_id}"
        
        # Prepare the payload in the desired format
        payload = {
            'DeviceTypeID': self.device_type_id,
            'TS': int(time.time()),  # Get current timestamp as an integer
            'Devs': [
                {
                    'ID': instance.device_info_id,
                    'Tags': [
                        {
                            'ID': tag_id,
                            'V': getattr(instance, tag_name)
                        }
                        for tag_id, tag_name in enumerate(instance.__dict__, start=1) if not tag_name.startswith('_')
                    ]
                }
            ]
        }

        self.client.publish(topic, json.dumps(payload))
        print(f"发布到 {topic}: {json.dumps(payload)}")

    def publish_all_devices_info(self, instances):
        """
        发布所有设备的状态信息
        """
        for instance in instances:
            self.publish_device_info(instance)
