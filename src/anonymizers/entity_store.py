import json
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from src.utils.logger import get_logger

logger = get_logger("EntityMappingStore")


class EntityMappingStore:
    """
    Thread-safe vault managing deterministic, stateful mappings between original PII strings
    and synthetic alternatives across the redaction lifecycle.
    
    Guarantees that when an entity (e.g., 'John Doe') is encountered multiple times across
    paragraphs, headers, or tables within the document (or across a batch run), it is always
    replaced by the exact same synthetic value ('Alexander Vance').
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self._lock = threading.RLock()
        # Mapping key: (entity_type, normalized_original_text) -> synthetic_value
        self._store: Dict[Tuple[str, str], str] = {}
        # Reverse mapping: synthetic_value -> (entity_type, original_text) for collision avoidance/auditing
        self._reverse_store: Dict[str, Tuple[str, str]] = {}
        # Counter for summary metrics: entity_type -> count of occurrences replaced
        self._metrics: Dict[str, int] = {}
        
        self.persistence_path = Path(persistence_path).resolve() if persistence_path else None
        if self.persistence_path and self.persistence_path.exists():
            self.load_from_vault()

    @staticmethod
    def normalize_key(entity_type: str, original_text: str) -> Tuple[str, str]:
        """
        Normalizes the original text to ensure deterministic hits despite minor spacing or case variations.
        """
        clean_text = " ".join(original_text.strip().split()).lower()
        return (entity_type.upper(), clean_text)

    def get_fake(self, entity_type: str, original_text: str) -> Optional[str]:
        """
        Retrieves the synthetic alternative for a given entity if already registered in the store.
        """
        key = self.normalize_key(entity_type, original_text)
        with self._lock:
            return self._store.get(key)

    def register_fake(self, entity_type: str, original_text: str, synthetic_value: str) -> str:
        """
        Registers a new synthetic value for an entity. If already registered, returns the existing value.
        Incrementally updates occurrence metrics.
        """
        key = self.normalize_key(entity_type, original_text)
        with self._lock:
            if key in self._store:
                existing_value = self._store[key]
                self._metrics[entity_type.upper()] = self._metrics.get(entity_type.upper(), 0) + 1
                return existing_value

            self._store[key] = synthetic_value
            self._reverse_store[synthetic_value] = (entity_type.upper(), original_text.strip())
            self._metrics[entity_type.upper()] = self._metrics.get(entity_type.upper(), 0) + 1
            logger.debug(
                f"Registered new mapping for [{entity_type}]: '{original_text[:15]}...' -> '{synthetic_value[:15]}...'"
            )
            
            if self.persistence_path:
                self.save_to_vault()
                
            return synthetic_value

    def get_metrics(self) -> Dict[str, int]:
        """
        Returns a dictionary of occurrence counts for each PII type processed.
        """
        with self._lock:
            return dict(self._metrics)

    def get_unique_counts(self) -> Dict[str, int]:
        """
        Returns the number of unique entities registered per PII type.
        """
        counts: Dict[str, int] = {}
        with self._lock:
            for (ent_type, _), _ in self._store.items():
                counts[ent_type] = counts.get(ent_type, 0) + 1
        return counts

    def clear(self) -> None:
        """
        Clears all in-memory mappings and metrics.
        """
        with self._lock:
            self._store.clear()
            self._reverse_store.clear()
            self._metrics.clear()
            logger.info("Entity mapping store cleared.")

    def save_to_vault(self) -> None:
        """
        Persists the current mapping store to a local JSON vault file.
        """
        if not self.persistence_path:
            return
        with self._lock:
            serializable_store = {
                f"{k[0]}::{k[1]}": v for k, v in self._store.items()
            }
            try:
                self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.persistence_path, "w", encoding="utf-8") as f:
                    json.dump(serializable_store, f, indent=2, ensure_ascii=False)
                logger.debug(f"Persisted entity mappings to {self.persistence_path}")
            except Exception as e:
                logger.error(f"Failed to save mapping vault: {e}")

    def load_from_vault(self) -> None:
        """
        Loads mappings from the JSON vault file if it exists.
        """
        if not self.persistence_path or not self.persistence_path.exists():
            return
        with self._lock:
            try:
                with open(self.persistence_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for composite_key, synthetic_value in data.items():
                    if "::" in composite_key:
                        ent_type, clean_text = composite_key.split("::", 1)
                        self._store[(ent_type, clean_text)] = synthetic_value
                        self._reverse_store[synthetic_value] = (ent_type, clean_text)
                logger.info(f"Loaded {len(self._store)} mappings from vault {self.persistence_path}")
            except Exception as e:
                logger.error(f"Failed to load mapping vault: {e}")
