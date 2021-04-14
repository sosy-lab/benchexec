import threading

class Counter(object):
    def __init__(self, start=0):
        self.lock = threading.Lock()
        self.value = start
    
    def increment(self):
        self.lock.acquire()
        try:
            self.value += 1
        finally:
            self.lock.release()