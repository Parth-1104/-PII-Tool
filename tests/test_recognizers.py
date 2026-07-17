import pytest
from src.recognizers.company_recognizer import CompanyNameRecognizer
from src.recognizers.ssn_recognizer import SSNRecognizer
from src.recognizers.dob_recognizer import DOBRecognizer
from src.recognizers.analyzer_factory import AnalyzerFactory


def test_company_name_recognizer_patterns():
    recognizer = CompanyNameRecognizer()
    text = "We signed a contract with Acme Technologies Inc. yesterday."
    results = recognizer.analyze(text=text, entities=["COMPANY_NAME"])
    
    assert len(results) > 0
    assert any(res.entity_type == "COMPANY_NAME" for res in results)
    assert any("Acme Technologies Inc." in text[res.start : res.end] for res in results)


def test_ssn_recognizer_strict_validation():
    recognizer = SSNRecognizer()
    
    # Valid SSN candidate
    valid_text = "The employee SSN is 123-45-6789 on file."
    valid_results = recognizer.analyze(text=valid_text, entities=["US_SSN"])
    assert len(valid_results) == 1
    assert valid_results[0].score >= 0.65

    # Invalid SSN due to 000 area code
    invalid_area_text = "Tracking ID 000-45-6789 should be ignored."
    invalid_area_results = recognizer.analyze(text=invalid_area_text, entities=["US_SSN"])
    assert len(invalid_area_results) == 0

    # Invalid SSN due to 00 group number
    invalid_group_text = "Part number 123-00-6789 is not an SSN."
    invalid_group_results = recognizer.analyze(text=invalid_group_text, entities=["US_SSN"])
    assert len(invalid_group_results) == 0


def test_dob_recognizer_context_boost():
    recognizer = DOBRecognizer()
    
    # Numeric date without context
    no_context_text = "The event happened on 05/14/1988 in town."
    res_no_ctx = recognizer.analyze(text=no_context_text, entities=["DATE_TIME"])
    assert len(res_no_ctx) == 1
    baseline_score = res_no_ctx[0].score

    # Numeric date with DOB context
    context_text = "Applicant DOB: 05/14/1988 confirmed."
    res_ctx = recognizer.analyze(text=context_text, entities=["DATE_TIME"])
    assert len(res_ctx) == 1
    assert res_ctx[0].score > baseline_score


def test_analyzer_factory_singleton():
    engine1 = AnalyzerFactory.get_engine()
    engine2 = AnalyzerFactory.get_engine()
    assert engine1 is engine2
    assert any("CompanyNameRecognizer" in r.name for r in engine1.registry.recognizers)



def test_custom_credit_card_recognizer_direct():
    """
    Explicit original architectural verification to ensure the custom
    English credit card pattern yields high-priority confidence matches.
    """
    from src.recognizers.analyzer_factory import AnalyzerFactory
    
    # Force load factory engine instance
    engine = AnalyzerFactory.get_engine(force_reload=True)
    
    # Test vector containing a mock credit card structure
    test_sample = "Transactional context visa verification pattern: 4111-2222-3333-4444"
    
    analysis_results = engine.analyze(text=test_sample, language="en")
    
    # Confirm that CREDIT_CARD entities are captured successfully
    cc_hits = [res for res in analysis_results if res.entity_type == "CREDIT_CARD"]
    
    assert len(cc_hits) > 0, "Custom credit card pattern failed to trace target entity."
    assert cc_hits[0].score == 1.0, "Recognizer logic missing high-priority confidence thresholding."
