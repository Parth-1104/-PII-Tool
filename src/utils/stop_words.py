"""
Stop words and common dictionary/vocabulary filtering utilities for high-precision PII detection.
Prevents common English words, standard corporate/legal headers, and general terminology
from being falsely identified as PII spans by spaCy NER or regex recognizers.
"""

from typing import Set

# Comprehensive set of common English words, financial/legal terminology, document structure terms,
# and standalone dates/months/numbers that must NOT be redacted when appearing without strong PII context.
COMMON_ENGLISH_WORDS: Set[str] = {
    # Document headers & structural keywords
    "table",
    "summary",
    "prospectus",
    "offering",
    "report",
    "content",
    "contents",
    "index",
    "section",
    "clause",
    "paragraph",
    "article",
    "appendix",
    "exhibit",
    "page",
    "note",
    "notes",
    "item",
    "part",
    "schedule",
    # Common corporate / governance terminology
    "company",
    "the company",
    "management",
    "board",
    "board of directors",
    "director",
    "directors",
    "officer",
    "officers",
    "executive",
    "executives",
    "shareholder",
    "shareholders",
    "stockholder",
    "stockholders",
    "principal",
    "common stock",
    "preferred stock",
    "securities",
    "shares",
    "equity",
    "capital",
    "dividend",
    "dividends",
    "issuer",
    "acquirer",
    "target",
    "subsidiary",
    "subsidiaries",
    "affiliate",
    "affiliates",
    "trust",
    "fund",
    "partnership",
    "business",
    "operations",
    "service",
    "services",
    "system",
    "systems",
    "product",
    "products",
    "market",
    "markets",
    "industry",
    "authority",
    "growth",
    "recently",
    "development",
    "developments",
    "general",
    "total",
    "net",
    "gross",
    "revenue",
    "revenues",
    "income",
    "loss",
    "losses",
    "asset",
    "assets",
    "liability",
    "liabilities",
    "cash",
    "debt",
    "agreement",
    "contract",
    "plan",
    "policy",
    "program",
    "project",
    "status",
    "risk",
    "risks",
    "statement",
    "statements",
    "forward-looking",
    "rule",
    "rules",
    "act",
    "code",
    "law",
    "regulation",
    "regulations",
    "commission",
    "united states",
    "state",
    "states",
    "federal",
    "national",
    "international",
    "global",
    "public",
    "private",
    "common",
    "certain",
    "various",
    "other",
    "such",
    "any",
    "all",
    "none",
    "some",
    "many",
    "most",
    "each",
    "every",
    "both",
    "either",
    "neither",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    # Months / standalone temporal words when not part of exact full date of birth
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
    "today",
    "yesterday",
    "tomorrow",
    "year",
    "years",
    "month",
    "months",
    "quarter",
    "quarters",
    "annual",
    "fiscal",
    "period",
    "periods",
    "date",
    "dates",
    "time",
    "times",
}

# Target PII entity types allowed in the system
TARGET_PII_ENTITIES: Set[str] = {
    "COMPANY_NAME",
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "US_SSN",
    "CREDIT_CARD",
    "DATE_TIME",
    "IP_ADDRESS",
}


def is_stop_word(text: str) -> bool:
    """
    Returns True if the normalized text is a common English word or generic document header.
    """
    if not text:
        return True
    cleaned = text.strip().lower()
    # Strip leading/trailing punctuation
    cleaned = cleaned.strip(".,;:!?()[]{}\"'`")
    if not cleaned:
        return True
    return cleaned in COMMON_ENGLISH_WORDS


def should_ignore_candidate(entity_type: str, text: str) -> bool:
    """
    Evaluates whether a candidate span detected by spaCy NER or regex should be ignored
    to maintain high precision and prevent false positives on common vocabulary.
    """
    if not text or not text.strip():
        return True

    cleaned = text.strip().lower().strip(".,;:!?()[]{}\"'`")
    if not cleaned:
        return True

    # If the span is in the common English words denylist, ignore it
    if cleaned in COMMON_ENGLISH_WORDS:
        return True

    # Ignore purely numeric strings or very short tokens (< 2 chars) unless specifically expected
    if len(cleaned) < 2 and entity_type not in ("US_SSN", "PHONE_NUMBER"):
        return True

    # For COMPANY_NAME: if it is a single lowercase or common word without suffixes, ignore
    if entity_type in ("COMPANY_NAME", "ORG"):
        words = cleaned.split()
        if len(words) == 1 and (cleaned in COMMON_ENGLISH_WORDS or cleaned.isalpha() and len(cleaned) <= 4):
            return True

    # For PERSON: single common dictionary words or title words should not be redacted as persons
    if entity_type in ("PERSON", "NAME"):
        if cleaned in COMMON_ENGLISH_WORDS:
            return True
        # If single word and common noun/verb/adjective
        words = cleaned.split()
        if len(words) == 1 and cleaned in {
            "director",
            "manager",
            "executive",
            "officer",
            "shareholder",
            "seller",
            "buyer",
            "client",
            "vendor",
            "trustee",
            "agent",
            "partner",
            "member",
            "holder",
        }:
            return True

    return False
