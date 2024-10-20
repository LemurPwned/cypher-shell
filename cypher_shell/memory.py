from collections import namedtuple

MemoryMessage = namedtuple("MemoryMessage", ["source", "type", "content"])


class Memory:
    def __init__(
        self,
        topk: int = 3,
        default_ignore_types: list[str] = ["error"],
        track_user_queries: bool = True,
    ):
        self.memory = []
        self.topk = topk
        self.default_ignore_types = default_ignore_types
        self.track_user_queries = track_user_queries
        self.user_queries = {}

    def check_user_query(self, query: str):
        return self.user_queries.get(query, None)

    def filter(self, ignore: list[str]):
        return [message for message in self.memory if message.type not in ignore]

    def filter_by_type(self, message_type: str):
        return [message for message in self.memory if message.type == message_type]

    def filter_by_source(self, source: str):
        return [message for message in self.memory if message.source == source]

    def add(self, message: MemoryMessage):
        self.memory.append(message)

    def add_user_result(self, query: str, result: str):
        self.memory.append(MemoryMessage(source="user", type="result", content=result))
        self.memory.append(MemoryMessage(source="user", type="query", content=query))
        if self.track_user_queries:
            self.user_queries[query] = result

    def __add__(self, message: MemoryMessage):
        self.add(message)

    def __str__(self):
        return "\n".join(
            [f"[{message.source}]: {message.content}" for message in self.memory]
        )

    def get(self):
        return self.filter(self.default_ignore_types)[-self.topk :]
