import re
from typing import List, Optional
from presidio_analyzer import (
    EntityRecognizer,
    Pattern,
    PatternRecognizer,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpArtifacts


class CompanyNameRecognizer(PatternRecognizer):
    """
    Custom Presidio Recognizer for detecting Company / Corporate Names (mapped to 'COMPANY_NAME').
    Combines spaCy Named Entity Recognition ('ORG' tokens) with high-precision regex patterns
    and corporate suffix keywords (Inc, LLC, Corp, GmbH, Limited, Technologies, Labs, etc.).
    """

    ENTITIES = ["COMPANY_NAME"]

    DEFAULT_PATTERNS = [
        Pattern(
            name="company_suffix_pattern",
            regex=r"(?-i:\b(?:[A-Z0-9][a-zA-Z0-9,&.-]*\s+){1,6}(?:Inc\.|Inc|LLC|L\.L\.C\.|Corp\.|Corp|Corporation|GmbH|Ltd\.|Ltd|Limited|Technologies|Labs|Solutions|Consulting|Enterprises|Group|Partners|Co\.|Company)(?:\b|(?=\s|$|[.,!?])))",
            score=0.75,
        ),
        Pattern(
            name="company_prefix_pattern",
            regex=r"(?-i:\b(?:The\s+)?(?:Bank|Hospital|University|Institute|Foundation|Agency|Association)\s+(?:[A-Z0-9][a-zA-Z0-9,&.-]*\s*){1,5}(?:\b|(?=\s|$|[.,!?])))",
            score=0.70,
        ),
    ]

    DEFAULT_CONTEXT = [
        "company",
        "employer",
        "workplace",
        "organization",
        "org",
        "corporate",
        "vendor",
        "client",
        "inc",
        "llc",
        "corp",
        "ltd",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        name: str = "CompanyNameRecognizer",
    ):
        patterns = patterns if patterns is not None else self.DEFAULT_PATTERNS
        context = context if context is not None else self.DEFAULT_CONTEXT
        super().__init__(
            supported_entity="COMPANY_NAME",
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def analyze(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        nlp_artifacts: Optional[NlpArtifacts] = None,
    ) -> List[RecognizerResult]:
        """
        Analyzes text using both pattern recognizer logic and spaCy ORG entities from nlp_artifacts.
        """
        results: List[RecognizerResult] = []

        # 1. Run regex pattern matching from parent class
        pattern_results = super().analyze(
            text=text, entities=entities, nlp_artifacts=nlp_artifacts
        )
        results.extend(pattern_results)

        # 2. Extract spaCy 'ORG' entities from NLP artifacts and map to COMPANY_NAME
        from src.utils.stop_words import should_ignore_candidate

        if nlp_artifacts and getattr(nlp_artifacts, "entities", None):
            for nlp_entity in nlp_artifacts.entities:
                entity_label = getattr(nlp_entity, "entity_type", getattr(nlp_entity, "label_", None))
                if entity_label in ("ORG", "ORGANIZATION"):
                    start_offset = getattr(nlp_entity, "start", getattr(nlp_entity, "start_char", 0))
                    end_offset = getattr(nlp_entity, "end", getattr(nlp_entity, "end_char", 0))
                    if start_offset is None or end_offset is None or start_offset >= end_offset:
                        continue

                    entity_text = text[int(start_offset):int(end_offset)]
                    if should_ignore_candidate("COMPANY_NAME", entity_text):
                        continue

                    # Calculate confidence score: only accept if corporate structure or strong context exists
                    has_suffix = any(
                        kw in entity_text.lower()
                        for kw in ["inc", "llc", "corp", "ltd", "tech", "group", "labs", "solutions", "partners", "enterprises", "company", "co.", "bank", "hospital", "university", "institute"]
                    )
                    start_ctx = max(0, int(start_offset) - 40)
                    end_ctx = min(len(text), int(end_offset) + 40)
                    surrounding = text[start_ctx:end_ctx].lower()
                    has_context = any(
                        kw in surrounding
                        for kw in ["company", "employer", "vendor", "client", "contract with", "signed with", "subsidiary", "acquired by", "corporation"]
                    )

                    if not has_suffix and not has_context:
                        # Single word or unconfirmed spaCy guess without corporate context -> assign low score below threshold
                        score = 0.35
                    else:
                        score = max(0.75, float(getattr(nlp_entity, "score", 0.75)))

                    from presidio_analyzer import AnalysisExplanation
                    explanation = AnalysisExplanation(
                        recognizer=self.name,
                        original_score=float(score),
                        textual_explanation=f"Detected COMPANY_NAME via spaCy ORG entity and rules by {self.name}",
                    )
                    meta = {
                        RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                        RecognizerResult.IS_SCORE_ENHANCED_BY_CONTEXT_KEY: False,
                    }
                    result = RecognizerResult(
                        entity_type="COMPANY_NAME",
                        start=int(start_offset),
                        end=int(end_offset),
                        score=float(score),
                        analysis_explanation=explanation,
                        recognition_metadata=meta,
                    )
                    results.append(result)

        # Ensure all results are RecognizerResult objects with non-None metadata and explanation before deduplicating
        clean_results = []
        from presidio_analyzer import AnalysisExplanation
        for item in results:
            etype = getattr(item, "entity_type", getattr(item, "label_", "COMPANY_NAME"))
            st = getattr(item, "start", getattr(item, "start_char", 0))
            en = getattr(item, "end", getattr(item, "end_char", 0))
            sc = getattr(item, "score", 0.65)

            span_text = text[int(st) : int(en)]
            if should_ignore_candidate(str(etype), span_text):
                continue

            meta = getattr(item, "recognition_metadata", None)
            if not isinstance(meta, dict):
                meta = {
                    RecognizerResult.RECOGNIZER_NAME_KEY: getattr(item, "recognizer_name", self.name),
                    RecognizerResult.IS_SCORE_ENHANCED_BY_CONTEXT_KEY: False,
                }
            explanation = getattr(item, "analysis_explanation", None)
            if not explanation or not hasattr(explanation, "set_supportive_context_word"):
                explanation = AnalysisExplanation(
                    recognizer=meta.get(RecognizerResult.RECOGNIZER_NAME_KEY, self.name),
                    original_score=float(sc),
                    textual_explanation=f"Detected {etype} by {self.name}",
                )

            clean_results.append(
                RecognizerResult(
                    entity_type=str(etype),
                    start=int(st),
                    end=int(en),
                    score=float(sc),
                    analysis_explanation=explanation,
                    recognition_metadata=meta,
                )
            )

        # Deduplicate overlapping or redundant results, keeping highest score
        return EntityRecognizer.remove_duplicates(clean_results)
