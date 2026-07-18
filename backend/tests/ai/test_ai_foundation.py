import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.ai.prompts.registry import PROMPTS, get_prompt
from app.ai.schemas.structured_output import DirectMessageAnalysisOutput
from app.ai.services.product_matching_service import ProductMatchResult


def test_prompt_registry_versions_are_explicit():
    assert {'DIRECT_MESSAGE_ANALYSIS','DIRECT_REPLY_SUGGESTION','DIRECT_ACTION_DRAFT','PRODUCT_MENTION_NORMALIZATION'} <= set(PROMPTS)
    assert get_prompt('DIRECT_MESSAGE_ANALYSIS').prompt_version == 'direct-message-analysis:v1'


def test_structured_output_normalizes_confidence_and_rejects_unknown_fields():
    payload={'language':'uk','intent':'ORDER_REQUEST','intent_confidence':94,'sentiment':'NEUTRAL','sentiment_confidence':'82','urgency':'NORMAL','requires_human':True,'clarification_required':True,'summary':'Клієнт хоче замовити.','extracted_entities':{'product_mentions':[{'text':'чорний годинник','quantity':1}]},'missing_fields':['phone'],'recommended_action':'ASK_CLARIFICATION','suggested_reply':'Уточніть телефон.'}
    result=DirectMessageAnalysisOutput.model_validate(payload)
    assert result.intent_confidence == pytest.approx(0.94)
    with pytest.raises(ValidationError):
        DirectMessageAnalysisOutput.model_validate(payload | {'provider_product_id':'unsafe'})


def test_evaluation_dataset_has_40_cases():
    cases=json.loads(Path('tests/fixtures/ai/direct_intelligence_cases.json').read_text())
    assert len(cases) >= 40
    assert all('expected' in case and 'intent' in case['expected'] for case in cases)


def test_product_match_result_defaults_to_human_review():
    result=ProductMatchResult(status='NOT_FOUND')
    assert result.matched_product_id is None
    assert result.clarification_required is True
