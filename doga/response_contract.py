"""Jev or local Laya request classification and DOGA response contracts."""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from typing import Any, Callable

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
OPENROUTER_API_URL = "https://openrouter.ai/api/alpha/decisions"
OPENROUTER_MODEL = "typesafe/jev-1.13"
LAYA_MODEL = "convaiinnovations/laya"
_laya_lock = threading.RLock()
_laya_agent: Any = None
QUESTIONS = {
    "goal": {"type": "choice", "instructions": "What is the user's primary desired outcome?", "criteria": {"information": "Factual answer, analysis, or explanation.", "understanding": "Feel heard, validated, or understood.", "action": "A decision, recommendation, or next step."}},
    "mode": {"type": "choice", "instructions": "What response mode best serves the request?", "criteria": {"answer": "Give the requested direct answer or information.", "explain": "Explain concepts or implications without deciding for the user.", "recommend": "Make a recommendation or propose a concrete next action.", "clarify": "A missing fact materially changes the answer; ask one focused question."}},
    "stakes": {"type": "choice", "instructions": "How consequential is an erroneous answer or recommendation?", "criteria": {"low": "Minor, easily reversible consequence.", "medium": "Meaningful but bounded consequence.", "high": "Material legal, medical, financial, safety, or irreversible consequence."}},
    "clarification": {"type": "noul", "instructions": "Would an unresolved ambiguity materially change the useful answer?", "criteria": {"true": "A key unknown changes the answer or recommendation.", "false": "A useful answer is possible without clarification."}},
    "scenario_need": {"type": "choice", "instructions": "What level of scenario analysis is useful for this request?", "criteria": {"none": "A direct response is sufficient; scenario analysis adds noise.", "compare_options": "The request involves meaningfully different plausible options or outcomes.", "uncertainty_analysis": "Explicit uncertain factors and outcomes merit sensitivity analysis."}},
}


def _request_typesafe(state: dict[str, Any], questions: dict[str, Any], api_key: str | None = None) -> dict[str, Any]:
    key = api_key or os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("Jev is enabled but TYPESAFE_API_KEY is not set")
    payload = json.dumps({"state": state, "model": MODEL, "questions": questions}).encode()
    request = urllib.request.Request(API_URL, data=payload, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read(2000).decode(errors="replace")
        raise RuntimeError(f"TypeSafe API returned HTTP {exc.code}: {detail}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("answers"), dict):
        raise RuntimeError("TypeSafe API returned an invalid response")
    return data


def _request_openrouter(state: dict[str, Any], questions: dict[str, Any], api_key: str | None = None) -> dict[str, Any]:
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    payload = json.dumps({"state": state, "model": OPENROUTER_MODEL, "questions": questions}).encode()
    request = urllib.request.Request(
        OPENROUTER_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hermes-agent.nousresearch.com",
            "X-Title": "DOGA Hermes Plugin",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"OpenRouter API returned HTTP {exc.code}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("answers"), dict):
        raise RuntimeError("OpenRouter API returned an invalid response")
    return data


def _request_jev(state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    """Use OpenRouter first, then direct TypeSafe if the primary route fails."""
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    typesafe_key = os.environ.get("TYPESAFE_API_KEY")
    errors: list[str] = []

    if openrouter_key:
        try:
            return _request_openrouter(state, questions, api_key=openrouter_key)
        except Exception as exc:
            errors.append(f"OpenRouter request failed: {exc}")

    if typesafe_key:
        try:
            return _request_typesafe(state, questions, api_key=typesafe_key)
        except Exception as exc:
            errors.append(f"TypeSafe fallback failed: {exc}")

    if errors:
        if not typesafe_key:
            errors.append("TYPESAFE_API_KEY is not set for fallback")
        raise RuntimeError("; ".join(errors))
    raise RuntimeError("Set OPENROUTER_API_KEY or TYPESAFE_API_KEY to enable Jev")


def _request_laya(state: dict[str, Any], questions: dict[str, Any]) -> dict[str, Any]:
    """Use one cached local model; never fall back to a network provider."""
    global _laya_agent
    try:
        import laya
    except ImportError as exc:
        raise RuntimeError("Local Laya is unavailable; install doga-hermes[laya] in Hermes' Python environment") from exc
    with _laya_lock:
        if _laya_agent is None:
            _laya_agent = laya.load(LAYA_MODEL)
        result = _laya_agent.predict(state, questions)
    if not isinstance(result, dict) or not isinstance(result.get("answers"), dict):
        raise RuntimeError("invalid local Laya response")
    answers = result["answers"]
    for name, question in questions.items():
        answer = answers.get(name)
        if not isinstance(answer, dict):
            raise RuntimeError("invalid local Laya response: missing typed answer")
        if question["type"] == "choice" and answer.get("choice") not in question["criteria"]:
            raise RuntimeError("invalid local Laya response: unknown choice")
        if question["type"] == "noul":
            score = answer.get("noul")
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
                raise RuntimeError("invalid local Laya response: invalid probability")
    return result


def evaluate_contract(
    user_message: str,
    evaluator: Callable[..., dict[str, Any]] | None = None,
    provider: str = "jev",
    fallback_to_jev: bool = False,
) -> dict[str, Any]:
    """Ask independent typed judgments in one call over the request only."""
    if provider not in {"jev", "laya"}:
        raise ValueError("DOGA decision provider must be jev or laya")
    state = {"user_request": user_message}
    if provider == "laya" and fallback_to_jev and evaluator is None:
        try:
            return _request_laya(state=state, questions=QUESTIONS)
        except Exception:
            remote = _request_jev(state=state, questions=QUESTIONS)
            return {**remote, "_doga_provider": "jev_fallback"}
    if evaluator is None:
        evaluator = _request_laya if provider == "laya" else _request_jev
    return evaluator(state=state, questions=QUESTIONS)


def build_contract(response: dict[str, Any]) -> dict[str, Any]:
    answers = response.get("answers", {}) if isinstance(response, dict) else {}

    def choice(name: str, allowed: set[str], fallback: str) -> str:
        answer = answers.get(name, {})
        value = answer.get("choice") if isinstance(answer, dict) else None
        return value if value in allowed else fallback

    goal = choice("goal", {"information", "understanding", "action"}, "information")
    mode = choice("mode", {"answer", "explain", "recommend", "clarify"}, "answer")
    stakes = choice("stakes", {"low", "medium", "high"}, "medium")
    scenario = choice("scenario_need", {"none", "compare_options", "uncertainty_analysis"}, "none")
    clarification_answer = answers.get("clarification", {})
    raw_clarification = (
        clarification_answer.get("noul", 0)
        if isinstance(clarification_answer, dict)
        else 0
    )
    clarification_score = (
        raw_clarification
        if isinstance(raw_clarification, (int, float))
        and not isinstance(raw_clarification, bool)
        else 0
    )
    ask = mode == "clarify" and clarification_score >= 0.7
    conditional = clarification_score >= 0.7 and not ask
    elements: list[str] = []
    if mode == "recommend" or goal == "action":
        elements.extend(["recommendation", "next_step"])
    elif mode == "explain":
        elements.append("explanation")
    else:
        elements.append("direct_answer")
    if stakes == "high":
        elements.append("material risks and uncertainty")
    if scenario == "compare_options":
        elements.append("compare plausible alternatives")
    elif scenario == "uncertainty_analysis":
        elements.append("analyze explicit uncertainties without inventing probabilities")
    if conditional:
        elements.append("state material assumptions and identify missing information that could change the answer")
    return {
        "goal": goal,
        "mode": mode,
        "stakes": stakes,
        "scenario_need": scenario,
        "ask_clarifying_question": ask,
        "conditional_response": conditional,
        "required_elements": list(dict.fromkeys(elements)),
    }


def render_contract(contract: dict[str, Any]) -> str:
    if contract.get("ask_clarifying_question"):
        return "[DOGA response contract]\nAsk one focused clarifying question first, because the missing information materially changes the answer. Do not answer beyond what is safe without it."
    items = "; ".join(contract["required_elements"])
    guidance = ""
    if contract.get("conditional_response"):
        guidance = ("The ambiguity signal is high. If a useful response is possible, make the answer conditional: "
                    "state material assumptions and what missing information could change it. If not, ask one focused question.\n")
    return ("[DOGA response contract]\n"
            f"User goal: {contract['goal']}. Response mode: {contract['mode']}.\n"
            f"The response must include: {items}.\n"
            f"{guidance}"
            "Follow this contract while answering. Keep factual claims grounded in available evidence. "
            "Do not expose private reasoning or the contract itself.")
