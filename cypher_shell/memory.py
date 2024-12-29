import json
from collections import namedtuple
from datetime import datetime

MemoryMessage = namedtuple("MemoryMessage", ["source", "type", "content"])


class FileLogger:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def log(self, message: str):
        with open(self.file_path, "a") as f:
            f.write(message + "\n")


class Memory:
    def __init__(
        self,
        topk: int = 3,
        default_ignore_types: list[str] = ("error",),
        track_user_queries: bool = True,
        write_to_file: bool = False,
    ):
        self.memory: list[MemoryMessage] = []
        self.topk: int = topk
        self.default_ignore_types: list[str] = default_ignore_types
        self.track_user_queries: bool = track_user_queries
        self.user_queries: dict[str, str] = {}
        self.write_to_file: bool = write_to_file
        if self.write_to_file:
            self.file_logger: FileLogger = FileLogger(
                file_path=f"query_logs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
            )

    def check_user_query(self, query: str) -> str | None:
        return self.user_queries.get(query, None)

    def filter(self, ignore: list[str]) -> list[MemoryMessage]:
        return [message for message in self.memory if message.type not in ignore]

    def filter_by_type(self, message_type: str) -> list[MemoryMessage]:
        return [message for message in self.memory if message.type == message_type]

    def filter_by_source(self, source: str) -> list[MemoryMessage]:
        return [message for message in self.memory if message.source == source]

    def add(self, message: MemoryMessage):
        self.memory.append(message)

    def add_user_result(self, user_query: str, machine_query: str, result: str, timing: float = -1):
        self.memory.append(MemoryMessage(source="user", type="result", content=result))
        self.memory.append(MemoryMessage(source="user", type="query", content=user_query))
        self.memory.append(MemoryMessage(source="system", type="query", content=machine_query))
        if self.track_user_queries:
            self.user_queries[user_query] = result
            if self.write_to_file:
                self.file_logger.log(
                    json.dumps(
                        {
                            "user_query": user_query,
                            "cypher_query": machine_query,
                            "timing": timing,
                        },
                        indent=4,
                    )
                )

    def __add__(self, message: MemoryMessage):
        self.add(message)

    def __str__(self):
        return "\n".join([f"[{message.source}]: {message.content}" for message in self.memory])

    def get(self):
        return self.filter(self.default_ignore_types)[-self.topk :]
