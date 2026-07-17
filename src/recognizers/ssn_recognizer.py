import re
from typing import List, Optional
from presidio_analyzer import (
    Pattern,
    PatternRecognizer,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpArtifacts


class SSNRecognizer(PatternRecognizer):
    """
    Enhanced US Social Security Number (US_SSN) Recognizer.
    Enforces strict structural and logical validation:
    - Area number (first 3 digits) cannot be 000, 666, or between 900-999.
    - Group number (middle 2 digits) cannot be 00.
    - Serial number (last 4 digits) cannot be 0000.
    - Supports both hyphenated (###-##-####) and space-separated (### ## ####) forms.
    """

    ENTITIES = ["US_SSN"]

    PATTERNS = [
        Pattern(
            name="us_ssn_hyphenated_or_spaced",
            regex=r"\b([0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{4})\b",
            score=0.65,
        )
    ]

    CONTEXT = [
        "ssn",
        "social security",
        "social security number",
        "tax id",
        "tin",
        "ss#",
        "soc sec",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        name: str = "SSNRecognizer",
    ):
        patterns = patterns if patterns is not None else self.PATTERNS
        context = context if context is not None else self.CONTEXT
        super().__init__(
            supported_entity="US_SSN",
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        """
        Validates the extracted SSN candidate against SSA issuance rules.
        """
        # Remove hyphens and spaces
        clean_digits = re.sub(r"[-\s]", "", pattern_text)
        if len(clean_digits) != 9 or not clean_digits.isdigit():
            return False

        area = int(clean_digits[0:3])
        group = int(clean_digits[3:5])
        serial = int(clean_digits[5:9])

        # SSA rules: area cannot be 000, 666, or 900-999
        if area == 0 or area == 666 or area >= 900:
            return False

        # Group number cannot be 00
        if group == 0:
            return False

        # Serial number cannot be 0000
        if serial == 0:
            return False

        return True

    def analyze(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        nlp_artifacts: Optional[NlpArtifacts] = None,
    ) -> List[RecognizerResult]:
        """
        Runs pattern analysis and filters out logically invalid SSN structures.
        If strong context words (e.g. 'ssn', 'social security') are present, boosts score.
        """
        results = super().analyze(
            text=text, entities=entities, nlp_artifacts=nlp_artifacts
        )
        validated_results: List[RecognizerResult] = []
        from presidio_analyzer import AnalysisExplanation
        from src.utils.stop_words import should_ignore_candidate

        for item in results:
            etype = getattr(item, "entity_type", getattr(item, "label_", "US_SSN"))
            st = getattr(item, "start", getattr(item, "start_char", 0))
            en = getattr(item, "end", getattr(item, "end_char", 0))
            sc = getattr(item, "score", 0.65)

            span_text = text[int(st) : int(en)]
            if should_ignore_candidate(str(etype), span_text):
                continue

            if self.validate_result(span_text):
                start_context = max(0, int(st) - 40)
                end_context = min(len(text), int(en) + 40)
                surrounding = text[start_context:end_context].lower()

                # Check for anti-context (tracking numbers, invoice IDs, part numbers)
                if any(bad in surrounding for bad in ["tracking", "invoice", "part#", "po#", "item#", "isbn", "serial"]):
                    continue

                score = float(sc)
                if any(kw in surrounding for kw in ["ssn", "social security", "tax id", "soc sec"]):
                    score = min(1.0, max(score, 0.85) + 0.30)
                elif "-" in span_text:
                    score = max(score, 0.75)

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
                        original_score=float(score),
                        textual_explanation=f"Detected {etype} by {self.name}",
                    )

                res = RecognizerResult(
                    entity_type=str(etype),
                    start=int(st),
                    end=int(en),
                    score=float(score),
                    analysis_explanation=explanation,
                    recognition_metadata=meta,
                )

                if res.analysis_explanation:
                    res.analysis_explanation.score = score
                validated_results.append(res)

        return validated_results
