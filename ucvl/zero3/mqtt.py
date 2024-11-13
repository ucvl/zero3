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
        self.instances = instances  # 保存设备实例
        self.publish_thread_stop = False
        
        # 连接到 MQTT 服务器并重试直到连接成功
        self.connect_mqtt(broker_ip, port)

    def connect_mqtt(self, broker_ip, port):
        """连接到 MQTT 服务器，如果连接失败，则每 1 分钟重试一次，直到成功"""
        while True:
            try:
                print("尝试连接到 MQTT 服务器...")
                self.client.connect(broker_ip, port, 60)
                self.client.loop_start()
                print("连接成功！")
                break  # 连接成功跳出循环
            except Exception as e:
                print(f"连接失败: {e}, 等待 1 分钟后重试...")
                time.sleep(60)  # 等待 60 秒后重试

    def on_connect(self, client, userdata, flags, rc):
        print(f"MQTT 连接成功, 状态码 {rc}")

    def on_message(self, client, userdata, msg):
        try:
            print(f"接收到消息: {msg.topic} -> {msg.payload.decode()}")
            payload = json.loads(msg.payload.decode())
            # 打印整个 payload 数据
            print("当前 payload 数据: ")
            print(json.dumps(payload, indent=4, ensure_ascii=False))  # 格式化输出
            if "Devs" not in payload:
                print("消息中缺少 'Devs' 字段，无法更新设备信息。")
                return

            # 遍历所有设备
            for dev in payload["Devs"]:
                dev_id = dev.get("DevID")
                if dev_id is None:
                    print("设备 ID 不存在，跳过该设备")
                    continue

                instance = self.get_device_instance_by_id(dev_id)
                if instance:
                    print(f"找到设备实例: {instance}")

                    # 更新设备的标签（Tags）
                    if "Tags" in dev:
                        for tag in dev["Tags"]:
                            tag_id = tag.get("ID")
                            real_value = tag.get("V")  # 这里使用 V 表示标签的实时值

                            if tag_id is not None and real_value is not None:
                                # 直接通过 tag_id 更新 Tags 字典中的 '实时值'
                                if tag_id in instance.Tags:
                                    print(f"更新标签 ID {tag_id} 的实时值为 {real_value}")
                                    instance.Tags[tag_id]['实时值'] = real_value  # 直接更新标签的实时值
                                else:
                                    print(f"未找到标签 ID {tag_id}，跳过该标签更新。")

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
        tags = []

        for tag_id, tag_data in instance.Tags.items():  # 遍历 Tags 字典
            if isinstance(tag_data, dict):  # 确保 tag_data 是字典
                real_value = tag_data.get("实时值")  # 获取实时值

                if real_value is not None:
                    tags.append({
                        'ID': tag_id,  # 使用 tag_id 作为标签的 ID
                        'V': real_value  # 使用实时值
                    })
                else:
                    print(f"警告: 标签 {tag_id} 没有实时值，跳过该标签。")
            else:
                print(f"警告: 标签 {tag_id} 的数据格式不正确，跳过该标签。")

        return {
            'DevID': instance.ID,  # 直接使用 instance.ID
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

    def subscribe_device_type(self, device_type_id,device_ID):
        """
        根据设备类型 ID 订阅相应的 MQTT 主题。
        :param device_type_id: 设备类型 ID
        """
        topic = f"AJB1/unified/{device_type_id}/{device_ID}"  # 订阅指定设备类型的所有设备主题
        self.client.subscribe(topic)
        print(f"已订阅主题: {topic}")
