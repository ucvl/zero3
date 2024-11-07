import pprint
import threading
import paho.mqtt.client as mqtt
import json
import time
class MQTTClient:
    def __init__(self, broker_ip, port, username, password, instances=None):
        self.client = mqtt.Client()
        self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(broker_ip, port, 60)
        self.client.loop_start()
        self.instances = instances  # 保存设备实例
        self.publish_thread_stop = False

    def on_connect(self, client, userdata, flags, rc):
        print(f"MQTT 连接成功, 状态码 {rc}")
        
    def on_message(self, client, userdata, msg):
        try:
            print(f"接收到消息: {msg.topic} -> {msg.payload.decode()}")
            payload = json.loads(msg.payload.decode())

            if "Devs" not in payload:
                print("消息中缺少 'Devs' 字段，无法更新设备信息。")
                return

            # 遍历所有设备
            for dev in payload["Devs"]:
                dev_id = dev.get("ID")
                if dev_id is None:
                    print("设备 ID 不存在，跳过该设备")
                    continue

                print(f"正在处理设备 ID: {dev_id}")
                instance = self.get_device_instance_by_id(dev_id)
                if instance:
                    print(f"找到设备实例: {instance.device_info_id}")

                    # 更新设备的标签（Tags）
                    if "Tags" in dev:
                        for tag in dev["Tags"]:
                            tag_id = tag.get("ID")
                            real_value = tag.get("V")  # 这里使用 V 表示标签的实时值

                            if tag_id is not None and real_value is not None:
                                # 使用 tag_metadata 来找到属性名称
                                tag_name = next((name for name, metadata in instance.tag_metadata.items() if metadata["ID"] == tag_id), None)

                                if tag_name:
                                    print(f"更新标签 '{tag_name}' 的实时值为 {real_value}")
                                    setattr(instance, tag_name, real_value)  # 动态更新标签的实时值
                                else:
                                    print(f"未找到标签 ID {tag_id}，跳过该标签更新。")
                            else:
                                print(f"标签 {tag_id} 没有实时值，跳过该标签更新。")
                else:
                    print(f"未找到设备实例 {dev_id}，跳过更新。")

        except json.JSONDecodeError:
            print(f"接收到的消息不是有效的 JSON 格式: {msg.payload.decode()}")
        except Exception as e:
            print(f"处理接收到的消息时发生错误: {e}")
 
    def get_device_instance_by_id(self, dev_id):
        """
        根据设备 ID 获取对应的设备实例
        """
        for instance in self.instances:
            if instance.ID == dev_id:  # 直接通过 instance.ID 访问 ID
                return instance
        return None

    def format_device_info(self, instance):
        """
        格式化设备信息为需要发布的数据格式
        """
        tags = [
            {
                'ID': tag["ID"],
                'V': getattr(instance, tag["Name"], None)
            }
            for tag in instance["Tags"]  # 假设 instance 中包含 device_type
        ]

        return {
            'ID': instance.ID,  # 直接使用 instance.ID
            'Tags': tags
        }

    def publish_all_devices_info(self, device_type_id):
        """
        发布指定类型设备的状态信息
        """
        devices_info = []

        for instance in self.instances:
            if instance.DevTypeID == device_type_id:
                devices_info.append(self.format_device_info(instance))

        if devices_info:  # 确保有设备信息才发布
            topic = f"AJB1/zero3/{device_type_id}"
            payload = {
                'DeviceTypeID': device_type_id,
                'TS': int(time.time()),
                'Devs': devices_info
            }

            self.client.publish(topic, json.dumps(payload))
            print(f"发布到 {topic}: {json.dumps(payload)}")

    def start_publish_loop(self, device_type_id, interval=5):
        """
        启动定时发布设备信息的循环。
        :param interval: 定时发布的间隔时间，默认为 5 秒
        """
        def loop():
            while not self.publish_thread_stop:
                self.publish_all_devices_info(device_type_id)
                time.sleep(interval)

        # 启动定时发布的线程
        publish_thread = threading.Thread(target=loop)
        publish_thread.daemon = True
        publish_thread.start()

    def stop_publish_loop(self):
        """停止定时发布循环"""
        self.publish_thread_stop = True
    def subscribe_device_type(self, device_type_id):
                """
                根据设备类型 ID 订阅相应的 MQTT 主题。
                :param device_type_id: 设备类型 ID
                """
                topic = f"AJB1/unified/{device_type_id}/+"  # 订阅指定设备类型的所有设备主题
                self.client.subscribe(topic)
                print(f"已订阅主题: {topic}")