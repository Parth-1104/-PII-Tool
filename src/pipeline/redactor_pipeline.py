from pathlib import Path
from typing import Union, Dict, Any, Optional
import yaml
from src.recognizers.analyzer_factory import AnalyzerFactory
from src.anonymizers.anonymizer_factory import AnonymizerFactory
from src.anonymizers.entity_store import EntityMappingStore
from src.document_processors.docx_processor import DocxProcessor
from src.utils.logger import get_logger
from src.utils.file_utils import backup_file

logger = get_logger("RedactionPipeline")


class RedactionPipeline:
    """
    End-to-end Orchestration Pipeline for the PII Redaction Tool.
    Unifies Presidio Analyzer, Anonymizer, EntityMappingStore, and DocxProcessor.
    Supports single file redaction and batch directory processing.
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        spacy_model: str = "en_core_web_lg",
        fallback_spacy_model: str = "en_core_web_sm",
        score_threshold: float = 0.65,
        enable_persistence: bool = False,
        persistence_path: Optional[str] = None,
    ):
        self.score_threshold = score_threshold
        self.enable_persistence = enable_persistence
        self.persistence_path = persistence_path
        self.spacy_model = spacy_model
        self.fallback_spacy_model = fallback_spacy_model

        if config_path and Path(config_path).exists():
            self._load_config(config_path)

        # Initialize core components
        logger.info("Initializing RedactionPipeline components...")
        self.analyzer = AnalyzerFactory.get_engine(
            spacy_model=self.spacy_model,
            fallback_model=self.fallback_spacy_model,
        )
        self.anonymizer = AnonymizerFactory.get_engine()
        self.entity_store = EntityMappingStore(
            persistence_path=self.persistence_path if self.enable_persistence else None
        )
        self.operators = AnonymizerFactory.get_operators(self.entity_store)
        logger.info("RedactionPipeline ready.")

    def _load_config(self, config_path: Union[str, Path]) -> None:
        """
        Loads configuration overrides from settings.yaml.
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            if cfg:
                nlp_cfg = cfg.get("nlp", {})
                self.spacy_model = nlp_cfg.get("spacy_model", self.spacy_model)
                self.fallback_spacy_model = nlp_cfg.get("fallback_spacy_model", self.fallback_spacy_model)

                redact_cfg = cfg.get("redaction", {})
                self.score_threshold = redact_cfg.get("default_score_threshold", self.score_threshold)
                self.enable_persistence = redact_cfg.get("enable_persistence", self.enable_persistence)
                self.persistence_path = redact_cfg.get("persistence_vault_path", self.persistence_path)
                logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Could not load config file {config_path}: {e}. Using defaults.")

    def redact_document(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        create_backup: bool = False,
        placeholder_image_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end PII redaction on a single `.docx` file.
        Includes options to filter out textual identifiers and overwrite internal media streams.
        
        Returns:
            Dictionary containing audit summary metrics (replacements, counts by PII type, etc.).
        """
        inp = Path(input_path).resolve()
        out = Path(output_path).resolve()

        logger.info(f"Starting redaction workflow: '{inp.name}' -> '{out.name}'")

        if create_backup:
            backup_file(inp)

        processor = DocxProcessor()
        processor.load(inp)

        # FIX: Added `placeholder_image_path` variable forwarding to handle visual assets dynamically
        process_metrics = processor.process_and_redact(
            analyzer_engine=self.analyzer,
            anonymizer_engine=self.anonymizer,
            operators=self.operators,
            score_threshold=self.score_threshold,
            placeholder_image_path=placeholder_image_path,
        )

        processor.save(out)

        # Collect summary auditing report
        summary = {
            "input_file": str(inp),
            "output_file": str(out),
            "paragraphs_processed": process_metrics.get("paragraphs_processed", 0),
            "total_replacements": process_metrics.get("total_replacements", 0),
            "images_redacted": process_metrics.get("images_redacted", 0),  # FIX: Extracted image metrics
            "entity_counts": self.entity_store.get_metrics(),
            "unique_entities_mapped": self.entity_store.get_unique_counts(),
        }

        logger.info(
            f"Successfully redacted '{inp.name}'. Summary metrics: {summary['entity_counts']}. "
            f"Images Redacted: {summary['images_redacted']}"
        )
        return summary

    def clear_mapping_store(self) -> None:
        """
        Clears stateful mappings in the entity store (useful between independent documents).
        """
        self.entity_store.clear()