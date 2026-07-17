import re
from typing import List, Optional
from presidio_analyzer import (
    Pattern,
    PatternRecognizer,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpArtifacts


class DOBRecognizer(PatternRecognizer):
    """
    Date of Birth (DOB) and Date/Time Recognizer (mapped to 'DATE_TIME').
    Captures common numerical and written date formats (e.g. MM/DD/YYYY, YYYY-MM-DD,
    January 15, 1985) and boosts confidence significantly when birth-related context
    keywords ('dob', 'birth', 'born') are present nearby.
    """

    ENTITIES = ["DATE_TIME"]

    PATTERNS = [
        # Numeric date patterns: MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, MM-DD-YYYY
        Pattern(
            name="numeric_date_slash_or_dash",
            regex=r"\b(?:(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}|(?:19|20)\d{2}[/-](?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12][0-9]|3[01]))\b",
            score=0.65,
        ),
        # Written date patterns: e.g. January 15, 1990 or 15 Jan 1990
        Pattern(
            name="written_month_date_year",
            regex=r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?,?\s+(?:19|20)\d{2}\b",
            score=0.70,
        ),
        Pattern(
            name="day_written_month_year",
            regex=r"\b(?:0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+(?:19|20)\d{2}\b",
            score=0.70,
        ),
    ]

    CONTEXT = [
        "dob",
        "date of birth",
        "birth",
        "born",
        "birthday",
        "birthdate",
        "d.o.b.",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        name: str = "DOBRecognizer",
    ):
        patterns = patterns if patterns is not None else self.PATTERNS
        context = context if context is not None else self.CONTEXT
        super().__init__(
            supported_entity="DATE_TIME",
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
        Analyzes text for date patterns and enhances confidence if birth context is discovered nearby.
        """
        results = super().analyze(
            text=text, entities=entities, nlp_artifacts=nlp_artifacts
        )
        enhanced_results: List[RecognizerResult] = []
        from presidio_analyzer import AnalysisExplanation
        from src.utils.stop_words import should_ignore_candidate, COMMON_ENGLISH_WORDS

        for item in results:
            etype = getattr(item, "entity_type", getattr(item, "label_", "DATE_TIME"))
            st = getattr(item, "start", getattr(item, "start_char", 0))
            en = getattr(item, "end", getattr(item, "end_char", 0))
            sc = getattr(item, "score", 0.65)

            span_text = text[int(st) : int(en)]
            if should_ignore_candidate(str(etype), span_text):
                continue

            # Check surrounding context
            start_context = max(0, int(st) - 40)
            end_context = min(len(text), int(en) + 40)
            surrounding = text[start_context:end_context].lower()
            has_birth_context = any(
                kw in surrounding for kw in ["dob", "birth", "born", "birthday", "birthdate", "d.o.b.", "age of"]
            )

            # If standalone year or standalone month or short string without birth context, discard
            cleaned_span = span_text.strip().strip(".,;:!?()[]{}")
            if not has_birth_context:
                if re.match(r"^(?:19|20)\d{2}$", cleaned_span) or cleaned_span.lower() in COMMON_ENGLISH_WORDS:
                    continue
                # If from spaCy or generic date without exact full pattern and without birth context, lower score
                recognizer_source = getattr(item, "recognizer_name", "")
                if recognizer_source != self.name and not re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", cleaned_span) and not re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b", cleaned_span, re.IGNORECASE):
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

            score = float(sc)
            if has_birth_context:
                score = min(1.0, max(0.85, score + 0.30))
            elif getattr(item, "recognizer_name", "") == self.name:
                score = max(0.65, score)

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
            enhanced_results.append(res)

        return enhanced_results
