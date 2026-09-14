import base64
import json
from pathlib import Path
from typing import Any

import pymupdf
import requests

from ai.config import settings
from .base import Ingestion


class MultiModalIngestion(Ingestion):
    """Convert a PDF/image into normalized multimodal elements and chunks."""

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

    def __init__(self, file_path: str, document_id: str | None = None, source_name: str | None = None):
        self.file_path = Path(file_path)
        self.document_id = document_id or self.file_path.stem
        self.source_name = source_name or self.file_path.name
        self.pages: list[dict[str, Any]] = []
        self.raw_elements: list[dict[str, Any]] = []
        self.elements: list[dict[str, Any]] = []
        self.chunks: list[dict[str, Any]] = []

    def extract_images(self) -> list[dict[str, Any]]:
        self.pages = []

        if self.file_path.suffix.lower() in self.IMAGE_EXTENSIONS:
            image_bytes = self.file_path.read_bytes()
            self.pages.append({"page_number": 1, "image": image_bytes})
            return self.pages

        if self.file_path.suffix.lower() != ".pdf":
            raise ValueError(f"Unsupported file type: {self.file_path.suffix}")

        with pymupdf.open(self.file_path) as document:
            for page_number, page in enumerate(document, start=1):
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                self.pages.append({
                    "page_number": page_number,
                    "image": pixmap.tobytes("png"),
                })

        return self.pages

    def extract_elements(self) -> list[dict[str, Any]]:
        if not self.pages:
            self.extract_images()

        self.raw_elements = []
        for page in self.pages:
            result = self._analyze_page(page["image"])
            page_elements = result.get("elements", [])
            self.raw_elements.append({
                "page_number": page["page_number"],
                "elements": page_elements,
            })
        return self.raw_elements

    def normalize_elements(self) -> list[dict[str, Any]]:
        if not self.raw_elements:
            self.extract_elements()

        self.elements = []
        source_name = self.file_path.name
        element_counter = 0

        for page in self.raw_elements:
            page_number = page["page_number"]
            for element in page.get("elements", []):
                content = self._content_to_text(element.get("content", ""))
                element_type = str(element.get("type", "paragraph")).lower().strip()
                if not content:
                    continue

                element_counter += 1
                self.elements.append({
                    "id": f"{self._safe_stem()}_p{page_number}_e{element_counter}",
                    "source": source_name,
                    "page_number": page_number,
                    "type": element_type,
                    "content": content,
                })

        return self.elements

    def create_chunks(
        self,
        max_characters: int | None = None,
        overlap: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.elements:
            self.normalize_elements()

        max_characters = max_characters or settings.CHUNK_SIZE
        overlap = overlap if overlap is not None else settings.CHUNK_OVERLAP

        chunks = []
        current_parts: list[str] = []
        current_elements: list[str] = []
        current_page = None
        current_heading = None
        chunk_counter = 0

        def flush_current() -> None:
            nonlocal chunk_counter
            if not current_parts:
                return
            text = "\n\n".join(current_parts).strip()
            if not text:
                return
            chunk_counter += 1
            chunks.append({
                "id": f"{self._safe_stem()}_chunk_{chunk_counter}",
                "source": self.source_name,
                "document_id": self.document_id,
                "page_number": current_page,
                "type": "text",
                "heading": current_heading,
                "content": text,
                "element_ids": list(current_elements),
            })
            current_parts.clear()
            current_elements.clear()

        for element in self.elements:
            element_type = element["type"]
            content = element["content"]

            if element_type == "heading":
                flush_current()
                current_heading = content
                current_page = element["page_number"]
                current_parts.append(content)
                current_elements.append(element["id"])
                continue

            if element_type in {"table", "chart", "diagram", "figure"}:
                flush_current()
                chunk_counter += 1
                chunks.append({
                    "id": f"{self._safe_stem()}_chunk_{chunk_counter}",
                    "source": self.source_name,
                    "document_id": self.document_id,
                    "page_number": element["page_number"],
                    "type": element_type,
                    "heading": current_heading,
                    "content": content,
                    "element_ids": [element["id"]],
                })
                continue

            if current_page is None:
                current_page = element["page_number"]

            candidate = "\n\n".join(current_parts + [content]).strip()
            if current_parts and len(candidate) > max_characters:
                flush_current()
                current_page = element["page_number"]
                if current_heading:
                    current_parts.append(current_heading)
                current_parts.append(content)
                current_elements.append(element["id"])
            else:
                current_parts.append(content)
                current_elements.append(element["id"])

        flush_current()

        # Split only oversized chunks while preserving metadata.
        final_chunks = []
        for chunk in chunks:
            if len(chunk["content"]) <= max_characters:
                final_chunks.append(chunk)
                continue
            parts = self._split_text(chunk["content"], max_characters, overlap)
            for index, part in enumerate(parts, start=1):
                split_chunk = dict(chunk)
                split_chunk["id"] = f"{chunk['id']}_{index}"
                split_chunk["content"] = part
                final_chunks.append(split_chunk)

        self.chunks = final_chunks
        return self.chunks

    def _analyze_page(self, image_bytes: bytes) -> dict[str, Any]:
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        prompt_path = settings.PROMPTS_DIR / "multimodal_ingestion.txt"
        prompt = prompt_path.read_text(encoding="utf-8")

        payload = {
            "model": settings.OLLAMA_VISION_MODEL,
            "prompt": prompt,
            "images": [encoded_image],
            "stream": False,
            "format": "json",
        }
        response = requests.post(
            f"{settings.OLLAMA_URL.rstrip('/')}/api/generate",
            json=payload,
            timeout=600,
        )
        response.raise_for_status()
        data = response.json()
        return json.loads(data["response"])

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        return json.dumps(content, ensure_ascii=False, indent=2).strip()

    def _safe_stem(self) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in self.file_path.stem)

    @staticmethod
    def _split_text(text: str, size: int, overlap: int) -> list[str]:
        if overlap >= size:
            overlap = max(0, size // 10)
        result = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            result.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(0, end - overlap)
        return result
