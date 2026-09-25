"""Jev-backed request classification and DOGA response contracts."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
OPENROUTER_API_URL = "https://openrouter.ai/api/alpha/decisions"
OPENROUTER_MODEL = "typesafe/jev-1.13"
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


def evaluate_contract(user_message: str, evaluator: Callable[..., dict[str, Any]] = _request_jev) -> dict[str, Any]:
    """Ask independent typed judgments in one call over the request only."""
    return evaluator(state={"user_request": user_message}, questions=QUESTIONS)


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
    ask = mode == "clarify" and isinstance(clarification_answer, dict) and clarification_answer.get("noul", 0) >= 0.7
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
    return {"goal": goal, "mode": mode, "stakes": stakes, "scenario_need": scenario, "ask_clarifying_question": ask, "required_elements": list(dict.fromkeys(elements))}


def render_contract(contract: dict[str, Any]) -> str:
    if contract.get("ask_clarifying_question"):
        return "[DOGA response contract]\nAsk one focused clarifying question first, because the missing information materially changes the answer. Do not answer beyond what is safe without it."
    items = "; ".join(contract["required_elements"])
    return ("[DOGA response contract]\n"
            f"User goal: {contract['goal']}. Response mode: {contract['mode']}.\n"
            f"The response must include: {items}.\n"
            "Follow this contract while answering. Keep factual claims grounded in available evidence. "
            "Do not expose private reasoning or the contract itself.")
