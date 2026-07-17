from typing import Dict, Any, Callable
from faker import Faker
from presidio_anonymizer.entities import OperatorConfig
from src.anonymizers.entity_store import EntityMappingStore
from src.utils.logger import get_logger

logger = get_logger("StatefulFakerOperator")


class StatefulFakerOperator:
    """
    Stateful Synthetic Data Generator using Faker and EntityMappingStore.
    Produces realistic synthetic alternatives for every detected PII span while strictly
    guaranteeing deterministic consistency (same entity -> same fake everywhere).
    """

    def __init__(self, entity_store: EntityMappingStore, locale: str = "en_US"):
        self.store = entity_store
        self.faker = Faker(locale)
        Faker.seed(42)  # Optional initial seed stability; subsequent calls are dynamic

    def generate(self, entity_type: str, original_text: str) -> str:
        """
        Main entrypoint called by Presidio Anonymizer CustomOperator for every span.
        Checks EntityMappingStore first. If missing, generates via domain provider and registers.
        """
        from src.utils.stop_words import TARGET_PII_ENTITIES
        ent_upper = entity_type.upper()
        if ent_upper == "DEFAULT" or (ent_upper not in TARGET_PII_ENTITIES and ent_upper not in ("NAME", "EMAIL", "PHONE", "COMPANY", "ORG", "ORGANIZATION", "ADDRESS", "GPE", "STREET_ADDRESS", "SSN", "TAX_ID", "BANK_ACCOUNT", "DATE_OF_BIRTH", "DOB", "DATE", "IPV4", "IP")):
            return original_text

        # Check if already mapped
        existing_fake = self.store.get_fake(entity_type, original_text)
        if existing_fake is not None:
            # Still increment occurrence counter via register_fake
            self.store.register_fake(entity_type, original_text, existing_fake)
            return existing_fake

        # Generate new fake value based on entity type
        synthetic_value = self._create_synthetic_for_type(entity_type, original_text)

        # Preserve case formatting if original was all uppercase (e.g., JOHN DOE -> ARTHUR PENDELTON)
        if original_text.isupper() and any(c.isalpha() for c in original_text):
            synthetic_value = synthetic_value.upper()

        # Register inside vault
        self.store.register_fake(entity_type, original_text, synthetic_value)
        return synthetic_value

    def _create_synthetic_for_type(self, entity_type: str, original_text: str) -> str:
        """
        Maps entity types to exact Faker generator methods.
        """
        ent = entity_type.upper()

        if ent in ("PERSON", "NAME", "FULL_NAME"):
            return self.faker.name()

        elif ent in ("EMAIL_ADDRESS", "EMAIL"):
            return self.faker.email()

        elif ent in ("PHONE_NUMBER", "PHONE"):
            return self.faker.phone_number()

        elif ent in ("COMPANY_NAME", "COMPANY", "ORG", "ORGANIZATION"):
            return self.faker.company()

        elif ent in ("LOCATION", "ADDRESS", "GPE", "STREET_ADDRESS"):
            # Replace newline in addresses with comma and space for DOCX line harmony
            return self.faker.address().replace("\n", ", ")

        elif ent in ("US_SSN", "SSN", "TAX_ID"):
            # Check if original had hyphens
            raw_ssn = self.faker.ssn()
            if "-" not in original_text and len(original_text.strip()) == 9:
                return raw_ssn.replace("-", "")
            return raw_ssn

        elif ent in ("CREDIT_CARD", "BANK_ACCOUNT"):
            return self.faker.credit_card_number()

        elif ent in ("DATE_TIME", "DATE_OF_BIRTH", "DOB", "DATE"):
            # If original string looks like MM/DD/YYYY numeric
            if "/" in original_text or "-" in original_text:
                dob = self.faker.date_of_birth(minimum_age=18, maximum_age=80)
                separator = "/" if "/" in original_text else "-"
                return dob.strftime(f"%m{separator}%d{separator}%Y")
            else:
                dob = self.faker.date_of_birth(minimum_age=18, maximum_age=80)
                return dob.strftime("%B %d, %Y")

        elif ent in ("IP_ADDRESS", "IPV4", "IP"):
            return self.faker.ipv4()

        else:
            # Default fallback for unlisted / unexpected entity types: preserve original text unchanged
            logger.debug(f"No specific Faker provider for entity [{ent}]; preserving original document text.")
            return original_text


def get_faker_operator_config(
    stateful_faker: StatefulFakerOperator, entity_type: str
) -> OperatorConfig:
    """
    Returns a Presidio OperatorConfig initialized with custom lambda delegating to StatefulFakerOperator.
    """
    return OperatorConfig(
        operator_name="custom",
        params={
            "lambda": lambda text: stateful_faker.generate(entity_type, text)
        },
    )
