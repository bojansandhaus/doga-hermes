from unittest.mock import patch

from doga.response_contract import build_contract, evaluate_contract, render_contract


def test_build_contract_uses_typed_answers_to_set_action_response_requirements():
    answers = {
        "goal": {"type": "choice", "choice": "action"},
        "mode": {"type": "choice", "choice": "recommend"},
        "stakes": {"type": "choice", "choice": "high"},
        "clarification": {"type": "noul", "noul": 0.1},
        "scenario_need": {"type": "choice", "choice": "compare_options"},
    }
    contract = build_contract({"answers": answers})
    assert contract["goal"] == "action"
    assert contract["mode"] == "recommend"
    assert contract["required_elements"] == ["recommendation", "next_step", "material risks and uncertainty", "compare plausible alternatives"]
    assert contract["ask_clarifying_question"] is False
    assert "recommendation" in render_contract(contract)


def test_ambiguous_contract_uses_safe_fallback():
    contract = build_contract({"answers": {"goal": {"choice": "surprise"}}})
    assert contract["goal"] == "information"
    assert contract["mode"] == "answer"
    assert contract["required_elements"] == ["direct_answer"]


def test_evaluate_contract_sends_bounded_structured_state_and_typed_questions():
    seen = {}

    def evaluator(**kwargs):
        seen.update(kwargs)
        return {"model": "jev-latest", "answers": {}}

    result = evaluate_contract("Should I switch jobs?", evaluator=evaluator)
    assert result["answers"] == {}
    assert seen["state"] == {"user_request": "Should I switch jobs?"}
    assert set(seen["questions"]) == {"goal", "mode", "stakes", "clarification", "scenario_need"}
    assert all("type" in question and "instructions" in question for question in seen["questions"].values())


def test_contract_requires_clarification_only_when_mode_and_signal_agree():
    contract = build_contract({"answers": {
        "goal": {"choice": "action"}, "mode": {"choice": "clarify"},
        "clarification": {"noul": 0.8},
    }})
    assert contract["ask_clarifying_question"] is True
    assert "clarifying question" in render_contract(contract)


def test_typesafe_http_request_uses_current_endpoint_and_secret_header():
    from doga import response_contract

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"answers": {}}'

    with patch.object(response_contract.urllib.request, "urlopen", return_value=FakeResponse()) as urlopen:
        response_contract._request_typesafe({"user_request": "hello"}, {"goal": {"type": "choice"}}, api_key="test-secret")
    request = urlopen.call_args.args[0]
    assert request.full_url == "https://api.typesafe.ai/v1/systemone"
    assert request.get_header("Authorization") == "Bearer test-secret"
