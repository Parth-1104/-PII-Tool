from typing import Optional
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from src.utils.logger import get_logger
from src.recognizers.company_recognizer import CompanyNameRecognizer
from src.recognizers.ssn_recognizer import SSNRecognizer
from src.recognizers.dob_recognizer import DOBRecognizer

logger = get_logger("AnalyzerFactory")


class AnalyzerFactory:
    """
    Singleton Factory class for building and configuring the Presidio AnalyzerEngine
    with custom spaCy NLP pipeline and custom domain recognizers.
    """

    _instance: Optional[AnalyzerEngine] = None

    @classmethod
    def get_engine(
        cls,
        spacy_model: str = "en_core_web_lg",
        fallback_model: str = "en_core_web_sm",
        force_reload: bool = False,
    ) -> AnalyzerEngine:
        """
        Returns a configured AnalyzerEngine instance.
        Attempts to load `spacy_model`; if missing, falls back to `fallback_model` or `en_core_web_sm`.
        """
        if cls._instance is not None and not force_reload:
            return cls._instance

        logger.info(f"Initializing Presidio AnalyzerEngine with spaCy model '{spacy_model}'...")

        import spacy

        # Check if primary model is installed; if not, fall back to fallback_model
        target_model = spacy_model
        if not spacy.util.is_package(target_model):
            logger.warning(
                f"Primary spaCy model '{target_model}' not installed. Falling back to '{fallback_model}'..."
            )
            target_model = fallback_model

        if not spacy.util.is_package(target_model):
            logger.warning(f"Fallback model '{target_model}' not found via spacy.util.is_package. Attempting load...")

        nlp_configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": target_model}],
        }

        nlp_engine = None
        try:
            provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
            nlp_engine = provider.create_engine()
        except (Exception, SystemExit) as e:
            logger.warning(
                f"Failed to load spaCy model '{target_model}': {e}. "
                f"Attempting fallback to '{fallback_model}'..."
            )
            fallback_configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": fallback_model}],
            }
            try:
                provider = NlpEngineProvider(nlp_configuration=fallback_configuration)
                nlp_engine = provider.create_engine()
            except (Exception, SystemExit) as e2:
                logger.error(f"Failed to load fallback spaCy model '{fallback_model}': {e2}")
                nlp_engine = None

        if nlp_engine:
            analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
        else:
            logger.warning("Using default Presidio AnalyzerEngine NLP engine configuration.")
            analyzer = AnalyzerEngine()

        # Register custom recognizers
        logger.debug("Registering custom recognizers: CompanyNameRecognizer, SSNRecognizer, DOBRecognizer")
        analyzer.registry.add_recognizer(CompanyNameRecognizer())
        analyzer.registry.add_recognizer(SSNRecognizer())
        analyzer.registry.add_recognizer(DOBRecognizer())

        cls._instance = analyzer
        logger.info("Presidio AnalyzerEngine initialized and configured successfully.")
        return cls._instance
