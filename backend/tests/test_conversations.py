"""
Tests for conversation detail API — prompt enhancement fields on messages.
"""

from tests.conftest import auth_headers


def test_conversation_detail_includes_prompt_enhancement(client, auth_token):
    # POST /chat persists original + enhanced prompts; GET detail should return them.
    chat_response = client.post(
        "/chat",
        json={"prompt": "Summarize quantum computing.", "enhance_prompt": True},
        headers=auth_headers(auth_token),
    )
    assert chat_response.status_code == 200
    conversation_id = chat_response.json()["conversation_id"]

    detail = client.get(
        f"/conversations/{conversation_id}",
        headers=auth_headers(auth_token),
    )

    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    assert len(assistant_msgs) >= 1

    assistant = assistant_msgs[0]
    assert assistant["original_prompt"] == "Summarize quantum computing."
    assert assistant["enhanced_prompt"]
    assert assistant["enhancement_method"] in ("ai", "rule_fallback", "disabled", "reused", "")
    if assistant.get("prompt_analysis"):
        assert assistant["prompt_analysis"]["persona"]
        assert assistant["prompt_analysis"]["complexity_level"] in (
            "simple",
            "medium",
            "complex",
        )
        assert "[Original user request" not in assistant["prompt_analysis"]["enhanced_prompt"]
