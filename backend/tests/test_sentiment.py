"""
Tests for sentiment analysis service and API.
"""

from services.sentiment_analyzer import (
    SENTIMENT_LABELS,
    analyze_sentiment,
    unknown_sentiment_result,
)
from tests.conftest import auth_headers


def test_analyze_positive_sentiment():
    result = analyze_sentiment("Thank you so much, this was really helpful and great!")

    assert result.label == "positive"
    assert result.confidence > 0
    assert result.explanation
    assert result.method == "rules"


def test_analyze_frustrated_sentiment():
    result = analyze_sentiment("This still isn't working and I'm so frustrated again.")

    assert result.label == "frustrated"
    assert result.confidence >= 0.55


def test_analyze_urgent_takes_priority_over_positive():
    result = analyze_sentiment("Thanks but I need this urgently by end of day ASAP.")

    assert result.label == "urgent"


def test_analyze_confused_sentiment():
    result = analyze_sentiment("I'm confused — can you clarify what this means?")

    assert result.label == "confused"


def test_analyze_excited_with_exclamation():
    result = analyze_sentiment("Wow this is amazing!! I'm so excited!")

    assert result.label == "excited"


def test_analyze_neutral_default():
    result = analyze_sentiment("List three colors.")

    assert result.label == "neutral"
    assert result.confidence >= 0.5


def test_unknown_sentiment_result_shape():
    result = unknown_sentiment_result()

    assert result.label == "unknown"
    assert result.confidence == 0.0
    assert "unable" in result.explanation.lower()


def test_all_labels_are_documented():
    sample = {
        "positive": "thank you great",
        "negative": "this is terrible and awful",
        "excited": "wow amazing excited",
        "frustrated": "frustrated not working",
        "confused": "confused clarify",
        "urgent": "urgent asap deadline",
        "neutral": "what is the capital of france",
    }
    for label in SENTIMENT_LABELS:
        assert label in sample
        assert analyze_sentiment(sample[label]).label == label


def test_sentiment_analyze_endpoint(client, auth_token):
    response = client.post(
        "/sentiment/analyze",
        json={"text": "I'm frustrated — this keeps failing."},
        headers=auth_headers(auth_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "frustrated"
    assert 0 <= body["confidence"] <= 100
    assert body["explanation"]


def test_sentiment_store_and_history(client, auth_token):
    chat = client.post(
        "/chat",
        json={"prompt": "Hello, thanks for your help!", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    assert chat.status_code == 200
    chat_body = chat.json()
    conversation_id = chat_body["conversation_id"]
    message_id = chat_body["user_message_id"]

    analyze = client.post(
        "/sentiment/analyze",
        json={
            "text": "Hello, thanks for your help!",
            "conversation_id": conversation_id,
            "message_id": message_id,
        },
        headers=auth_headers(auth_token),
    )
    assert analyze.status_code == 200
    assert analyze.json()["label"] == "positive"

    history = client.get(
        f"/sentiment/conversations/{conversation_id}/history",
        headers=auth_headers(auth_token),
    )
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) >= 1
    assert items[-1]["message_id"] == message_id


def test_conversation_detail_includes_sentiment(client, auth_token):
    chat = client.post(
        "/chat",
        json={"prompt": "URGENT: need this fixed immediately", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    conversation_id = chat.json()["conversation_id"]
    message_id = chat.json()["user_message_id"]

    client.post(
        "/sentiment/analyze",
        json={
            "text": "URGENT: need this fixed immediately",
            "conversation_id": conversation_id,
            "message_id": message_id,
        },
        headers=auth_headers(auth_token),
    )

    detail = client.get(
        f"/conversations/{conversation_id}",
        headers=auth_headers(auth_token),
    )
    assert detail.status_code == 200
    user_messages = [m for m in detail.json()["messages"] if m["role"] == "user"]
    assert user_messages[-1]["sentiment"] is not None
    assert user_messages[-1]["sentiment"]["label"] == "urgent"
