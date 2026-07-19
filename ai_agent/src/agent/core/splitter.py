"""Stateless document text splitter abstraction and implementations."""

import os
from abc import ABC, abstractmethod
from langchain_text_splitters import MarkdownTextSplitter, RecursiveCharacterTextSplitter


class BaseDocumentSplitter(ABC):
    """Abstract base class for all file text splitters."""

    @abstractmethod
    def split(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
        """Split document text into smaller semantically cohesive chunks.

        Args:
            text: The raw text content of the document.
            chunk_size: Maximum characters per chunk.
            chunk_overlap: Number of overlapping characters between adjacent chunks.

        Returns:
            A list of text segments.
        """
        pass


class MarkdownDocumentSplitter(BaseDocumentSplitter):
    """Document splitter specialized for Markdown content using headers."""

    def split(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
        """Split Markdown text preserving headers and block structure."""
        splitter = MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        return splitter.split_text(text)


class RecursiveTextSplitter(BaseDocumentSplitter):
    """Generic document splitter utilizing recursive character rules."""

    def split(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
        """Split plain text recursively by paragraphs, sentences, and words."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        return splitter.split_text(text)


class DocumentSplitterFactory:
    """Registry and factory resolving splitters by filename extensions."""

    @staticmethod
    def get_splitter(file_name: str) -> BaseDocumentSplitter:
        """Resolve and return the appropriate splitter based on file extension.

        Args:
            file_name: The name or path of the file to ingest.

        Returns:
            An instance of BaseDocumentSplitter.
        """
        _, ext = os.path.splitext(file_name.lower())
        if ext in {".md", ".markdown"}:
            return MarkdownDocumentSplitter()
        return RecursiveTextSplitter()
