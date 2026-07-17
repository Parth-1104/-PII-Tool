from typing import Dict, Optional
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from src.anonymizers.entity_store import EntityMappingStore
from src.anonymizers.fake_operators import StatefulFakerOperator, get_faker_operator_config
from src.utils.logger import get_logger

logger = get_logger("AnonymizerFactory")


class AnonymizerFactory:
    """
    Singleton Factory class for building the Presidio AnonymizerEngine
    and constructing the comprehensive dictionary of custom stateful Faker operators.
    """

    _instance: Optional[AnonymizerEngine] = None

    @classmethod
    def get_engine(cls) -> AnonymizerEngine:
        """
        Returns a singleton instance of Presidio's AnonymizerEngine.
        """
        if cls._instance is None:
            cls._instance = AnonymizerEngine()
            logger.debug("Presidio AnonymizerEngine initialized.")
        return cls._instance

    @classmethod
    def get_operators(
        cls, entity_store: EntityMappingStore, locale: str = "en_US"
    ) -> Dict[str, OperatorConfig]:
        """
        Constructs and returns the complete operator configuration dictionary mapping
        every target PII entity type to our StatefulFakerOperator.
        """
        stateful_faker = StatefulFakerOperator(entity_store, locale=locale)

        # All target entity types requiring custom Faker replacement
        supported_entities = [
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "COMPANY_NAME",
            "LOCATION",
            "US_SSN",
            "CREDIT_CARD",
            "DATE_TIME",
            "IP_ADDRESS",
            "ORG",
            "GPE",
            "DEFAULT",
        ]

        operators: Dict[str, OperatorConfig] = {}
        for ent in supported_entities:
            operators[ent] = get_faker_operator_config(stateful_faker, ent)

        logger.debug(f"Constructed custom Faker operators for {len(operators)} entity types.")
        return operators
