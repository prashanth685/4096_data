import math
import time
import paho.mqtt.publish as publish
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtWidgets import QApplication
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MQTTPublisher(QObject):
    def __init__(self, broker, topics):
        super().__init__()
        self.broker = broker
        self.topics = topics if isinstance(topics, list) else [topics]
        self.count = 0

        self.frequency = 7
        self.amplitude = (46537 - 16390) / 2
        self.offset = (46537 + 16390) / 2

        self.sample_rate = 4096
        self.time_per_message = 1.0
        self.current_time = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_message)
        self.timer.start(1000)

    def publish_message(self):
        if self.count < 50:
            values = []
            for i in range(self.sample_rate):
                t = self.current_time + (i / self.sample_rate)
                value = self.offset + self.amplitude * math.sin(1 * math.pi * self.frequency * t)
                values.append(round(value, 2))

            self.current_time += 1
            message = ",".join(map(str, values))

            for topic in self.topics:
                try:
                    publish.single(topic, message, hostname=self.broker, qos=1)
                    logging.info(f"[{self.count}] Published to {topic}: {message[:50]}... ({self.sample_rate} values)")
                except Exception as e:
                    logging.error(f"Failed to publish to {topic}: {str(e)}")

            self.count += 1
        else:
            self.timer.stop()
            logging.info("Publishing stopped after 50 messages.")

if __name__ == "__main__":
    app = QApplication([])
    broker = "192.168.1.173"
    topics = ["sarayu/tag2/topic2|m/s"]
    mqtt_publisher = MQTTPublisher(broker, topics)
    app.exec_()