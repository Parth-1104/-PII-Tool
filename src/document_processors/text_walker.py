from typing import List, Tuple, Any
from src.utils.logger import get_logger

logger = get_logger("TextRunWalker")


class TextRunWalker:
    """
    Intelligent Text Run Merger & Slice Replacement Utility for python-docx Paragraphs.
    
    Solves the 'Split Run Problem' where Microsoft Word fragments words or PII entities across
    multiple XML text runs (<w:r>) due to spellcheck markers, revision tracking, or styling tags.
    
    Reconstructs full contiguous paragraph text for high-precision Presidio NLP analysis,
    then projects synthetic replacements back across the exact affected run slices (right-to-left)
    to guarantee zero loss of document formatting (fonts, colors, bold/italics).
    """

    @staticmethod
    def extract_runs_and_text(paragraph: Any) -> Tuple[str, List[Tuple[int, int, Any]]]:
        """
        Iterates over paragraph.runs and builds:
        1. Full concatenated paragraph string (`full_text`).
        2. Interval mapping index: List of (start_char_idx, end_char_idx, run_object).
        """
        full_text_parts = []
        run_spans = []
        current_offset = 0

        for run in paragraph.runs:
            text = run.text
            if not text:
                continue
            run_len = len(text)
            full_text_parts.append(text)
            run_spans.append((current_offset, current_offset + run_len, run))
            current_offset += run_len

        full_text = "".join(full_text_parts)
        return full_text, run_spans

    @classmethod
    def apply_replacements(
        cls,
        paragraph: Any,
        replacements: List[Tuple[int, int, str]],
    ) -> int:
        """
        Applies a list of PII replacements to the paragraph runs.
        
        Args:
            paragraph: python-docx Paragraph object.
            replacements: List of tuples `(pii_start_char, pii_end_char, synthetic_text)`.
        
        Returns:
            Number of successful replacements made in this paragraph.
        """
        if not replacements or not paragraph.runs:
            return 0

        # Extract up-to-date run mapping
        _, run_spans = cls.extract_runs_and_text(paragraph)
        if not run_spans:
            return 0

        # Sort replacements descending by start offset (right-to-left)
        # This prevents length modifications from invalidating leftward character offsets
        sorted_replacements = sorted(replacements, key=lambda x: x[0], reverse=True)
        replaced_count = 0

        for pii_start, pii_end, synthetic_text in sorted_replacements:
            if pii_start >= pii_end:
                continue

            # Find all runs overlapping with [pii_start, pii_end)
            overlapping_runs = []
            for r_start, r_end, run_obj in run_spans:
                # Check for interval overlap: max(start1, start2) < min(end1, end2)
                overlap_start = max(pii_start, r_start)
                overlap_end = min(pii_end, r_end)
                if overlap_start < overlap_end:
                    # Convert document-level offsets to run-local offsets
                    local_start = overlap_start - r_start
                    local_end = overlap_end - r_start
                    overlapping_runs.append((run_obj, local_start, local_end))

            if not overlapping_runs:
                continue

            # Project replacement onto the first overlapping run
            first_run, first_local_start, first_local_end = overlapping_runs[0]
            first_run_text = first_run.text
            first_run.text = (
                first_run_text[:first_local_start]
                + synthetic_text
                + first_run_text[first_local_end:]
            )

            # Empty the affected slices of any subsequent overlapping runs
            for subsequent_run, sub_local_start, sub_local_end in overlapping_runs[1:]:
                sub_text = subsequent_run.text
                subsequent_run.text = sub_text[:sub_local_start] + "" + sub_text[sub_local_end:]

            replaced_count += 1

        return replaced_count
