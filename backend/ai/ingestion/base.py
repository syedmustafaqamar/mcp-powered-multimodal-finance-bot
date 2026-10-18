from abc import ABC, abstractmethod
from typing import Any


class Ingestion(ABC):
    @abstractmethod
    def extract_images(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def extract_elements(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def normalize_elements(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create_chunks(self) -> list[dict[str, Any]]:
        raise NotImplementedError
