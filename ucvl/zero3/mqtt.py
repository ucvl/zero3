import paho.mqtt.client as mqtt
import json
import time

class MQTTClient:
    def __init__(self, broker_ip, port, username, password, device_type_id=1,instances=None):
        self.client = mqtt.Client()
        self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message  # 确保设置 on_message 回调
        self.client.connect(broker_ip, port, 60)
        self.client.loop_start()
        self.device_type_id = device_type_id  # Set the default DeviceTypeID
        self.instances = instances  # 保存设备实例
        # 订阅特定主题
        self.client.subscribe(f"AJB1/unified/{self.device_type_id}/+")
    def on_connect(self, client, userdata, flags, rc):
        print(f"MQTT 连接成功, 状态码 {rc}")
    def on_message(self, client, userdata, msg):
            """
            当接收到消息时，处理更新设备的实时值
            """
            try:
                print(f"接收到消息: {msg.topic} -> {msg.payload.decode()}")
                # 解析消息 payload
                payload = json.loads(msg.payload.decode())

                # 从主题中提取设备 ID
                topic_parts = msg.topic.split('/')
                device_id = topic_parts[-1]  # 设备 ID 是主题的最后一部分

                # 更新对应设备的实时值
                for instance in self.instances:
                    if instance.device_info_id == device_id:  # 根据设备 ID 查找对应设备
                        for tag in payload["Tags"]:
                            tag_name = tag["Name"]
                            # 更新设备实例的对应实时值
                            if hasattr(instance, tag_name):
                                setattr(instance, tag_name, tag["V"])
                                print(f"更新设备 {device_id} 的 {tag_name} 为 {tag['V']}")
                        break
            except Exception as e:
                print(f"处理接收到的消息时发生错误: {e}")
    def get_mqtt_topic(self, device_id):
        """
        根据设备ID生成MQTT主题
        """
        return f"AJB1/zero3/{self.device_type_id}/{device_id}"

    def format_device_info(self, instance, device_types):
        """
        格式化设备信息为需要发布的数据格式
        """
        device = next((d for d in device_types if d["ID"] == instance.DevTypeID), None)
        if not device:
            raise ValueError(f"Device with ID {instance.DevTypeID} not found in device_types.")

        tags = [
            {
                'ID': tag["ID"],
                'V': getattr(instance, tag["Name"], None)
            }
            for tag in device["Tags"]
        ]

        return {
            'ID': instance.device_info_id,
            'Tags': tags
        }

    def publish_all_devices_info(self, instances, device_types):
        """
        发布指定类型设备的状态信息
        """
        # 只发布当前设备类型的所有设备信息
        devices_info = []

        for instance in instances:
            if instance.DevTypeID == self.device_type_id:  # 只发布该设备类型的设备
                devices_info.append(self.format_device_info(instance, device_types))

        if devices_info:  # 确保有设备信息才发布
            topic = f"AJB1/zero3/{self.device_type_id}"  # 发布到所有设备的主题
            payload = {
                'DeviceTypeID': self.device_type_id,
                'TS': int(time.time()),  # 获取当前时间戳
                'Devs': devices_info  # 所有设备信息放入 Devs 数组
            }

            self.client.publish(topic, json.dumps(payload))
            print(f"发布到 {topic}: {json.dumps(payload)}")
