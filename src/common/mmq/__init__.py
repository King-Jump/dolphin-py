""" Memory Message Queue just for prototype
"""

from typing import Tuple
import threading


MAX_MESSAGES = 10_000

class MMQTopic:
    SPOT_NEW = "spot_new"
    SPOT_CANCEL = "spot_cancel"
    FUNDING_NEW = "funding_new"
    FUNDING_CANCEL = "funding_cancel"

    SPOT_MATCH_OUT = "spot_match_out"

class MMQ:
    """ store messages in memory, clear half of messages when it's full
    """
    def __init__(self):
        self.lock = threading.Lock()

        self.messages = {}
        # current offset = base + offset
        self.messages_base = {}
        self.messages_offset = {}
        
    def produce(self, topic: str, message: str):
        if topic not in self.messages:
            self.messages[topic] = []
            self.messages_base[topic] = 0
            self.messages_offset[topic] = 0

        with self.lock:
            self.messages[topic].append(message)
            if len(self.messages[topic]) >= MAX_MESSAGES:
                size = int(0.5 * MAX_MESSAGES)
                self.messages[topic] = self.messages[topic][size:]
                self.messages_base[topic] += size

    def consume(self, topic: str, offset: int = 0) -> Tuple[int, str]:
        """
        """
        if topic not in self.messages:
            return 0, ""

        with self.lock:
            if offset and offset >= self.messages_base[topic]:
                relative_offset = offset - self.messages_base[topic]
                self.messages_offset[topic] = relative_offset
            relative_offset = self.messages_offset[topic]
            if relative_offset >= len(self.messages[topic]):
                return offset, ""
            return offset, self.messages[topic][relative_offset]

FUNDING_MATCH_MQ = MMQ()
MATCH_FUNDING_MQ = MMQ()