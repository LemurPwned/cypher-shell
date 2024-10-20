class Memory:
    def __init__(self, topk: int = 3):
        self.memory = []
        self.topk = topk

    def add(self, message: str):
        self.memory.append(message)

    def get(self):
        return self.memory[-self.topk :]
