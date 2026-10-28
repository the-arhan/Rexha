"""Unit tests for deterministic intent parser and LLM fallback adapter."""

import pytest
from rexha.intelligence.intent_parser import IntentParser, LLMPlanner
from rexha.orchestration.actions import StructuredAction


def test_intent_parser_status():
    parser = IntentParser()
    actions = parser.parse("status")
    assert len(actions) == 1
    assert actions[0].action_name == "system.get_status"


def test_intent_parser_windows():
    parser = IntentParser()
    actions = parser.parse("list windows")
    assert len(actions) == 1
    assert actions[0].action_name == "window.list"


def test_intent_parser_app_launch():
    parser = IntentParser()
    actions = parser.parse("open visual studio code")
    assert len(actions) == 1
    assert actions[0].action_name == "application.open"
    assert actions[0].arguments["executable"] == "visual studio code"


def test_intent_parser_sleep():
    parser = IntentParser()
    actions = parser.parse("sleep")
    assert len(actions) == 1
    assert actions[0].action_name == "ui.sleep"


class DummyPlanner(LLMPlanner):
    def plan_task(self, prompt: str) -> list[StructuredAction]:
        return [StructuredAction(action_name="custom.ai_plan", description=f"Plan for: {prompt}")]


def test_intent_parser_llm_fallback():
    planner = DummyPlanner()
    parser = IntentParser(llm_planner=planner)
    actions = parser.parse("organize all open windows on my left display")
    assert len(actions) == 1
    assert actions[0].action_name == "custom.ai_plan"

