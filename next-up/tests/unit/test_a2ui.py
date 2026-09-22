"""Unit tests for A2UI prompt schema and after_model_callback integration."""

import json
from google.genai import types
from google.adk.models.llm_response import LlmResponse
from app.agent import root_agent
from app.a2ui_utils import a2ui_callback


def test_root_agent_a2ui_configuration():
    """Verify root_agent has A2UI system prompt and after_model_callback wired."""
    assert root_agent.after_model_callback is not None
    assert root_agent.after_model_callback == a2ui_callback
    assert "beginRendering" in root_agent.instruction
    assert "surfaceUpdate" in root_agent.instruction
    assert "Card" in root_agent.instruction


def test_a2ui_callback_passthrough_plain_text():
    """Verify plain text without A2UI keywords is left alone."""
    response = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="Hello! How can I help you discover a movie today?")],
        )
    )
    result = a2ui_callback(None, response)
    assert result is None


def test_a2ui_callback_rewraps_a2ui_json():
    """Verify valid A2UI JSON text is transformed into adk web datapart blob."""
    sample_a2ui = [
        {"beginRendering": {"surfaceId": "surface-1", "root": "card-1"}},
        {
            "surfaceUpdate": {
                "surfaceId": "surface-1",
                "components": [
                    {
                        "id": "card-1",
                        "component": {
                            "Card": {
                                "child": "text-1"
                            }
                        }
                    },
                    {
                        "id": "text-1",
                        "component": {
                            "Text": {
                                "text": {"literalString": "Severance (Apple TV+)"},
                                "usageHint": "h1"
                            }
                        }
                    }
                ]
            }
        }
    ]
    json_text = json.dumps(sample_a2ui)
    response = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=f"<a2ui-json>{json_text}</a2ui-json>")],
        )
    )
    result = a2ui_callback(None, response)
    assert result is not None
    assert result.custom_metadata == {"a2a:response": "true"}
    assert result.content is not None
    assert len(result.content.parts) == 2
    part0 = result.content.parts[0]
    assert part0.inline_data is not None
    assert part0.inline_data.mime_type == "text/plain"
    assert b"<a2a_datapart_json>" in part0.inline_data.data
