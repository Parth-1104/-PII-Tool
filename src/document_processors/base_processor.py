from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Dict, Any


class BaseDocumentProcessor(ABC):
    """
    Abstract Base Class for enterprise document processors.
    Defines the contract for loading, iterating text blocks, redacting, and saving documents.
    Enforces extensibility for multi-format expansion (.docx, .pdf, .xlsx, etc.).
    """

    @abstractmethod
    def load(self, file_path: Union[str, Path]) -> None:
        """
        Loads the document from the file system into memory.
        """
        pass

    @abstractmethod
    def process_and_redact(
        self,
        analyzer_engine: Any,
        anonymizer_engine: Any,
        operators: Dict[str, Any],
        score_threshold: float = 0.50,
    ) -> Dict[str, Any]:
        """
        Traverses the document, executes PII detection and stateful synthetic replacement,
        and returns auditing metrics.
        """
        pass

    @abstractmethod
    def save(self, output_path: Union[str, Path]) -> None:
        """
        Persists the modified document to disk.
        """
        pass
