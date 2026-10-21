from typing import Dict, List, Optional

Message = Dict[str, str]  # {"role": "system"|"user"|"assistant", "content": "..."}


class ProviderError(Exception):
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class Provider:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def chat(self, model: str, messages: List[Message], temperature: float = 0.7,
             max_tokens: int = 1500) -> str:
        raise NotImplementedError
