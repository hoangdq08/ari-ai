"""Unit tests for prompt_guard.basic_chat_response.

Focus on the social-invitation catch path (regression for the
"tối đi cà phê không em?" leak into RAG/LLM) plus the existing
greeting/thanks/goodbye/capability branches so they do not regress.
"""

from __future__ import annotations

import pytest

from app.ml_agri_chat.modules.prompt_guard import basic_chat_response


SOCIAL_INVITATION_PROMPTS = [
    "tối đi cà phê không em?",
    "đi cafe không",
    "làm ly cà phê nhé",
    "tách cà phê sáng nay",
    "rủ đi cà phê chiều nay",
    "tối nay đi nhậu",
    "đi chơi không",
    "mình hẹn hò nhé",
    "đi cf đi",
]

AGRI_PROMPTS_SHOULD_PASS_TO_RAG = [
    "cây cà phê bị bệnh gì?",
    "cách chăm sóc cà phê",
    "bón phân cho cà phê arabica",
    "thu hoạch cà phê khi nào",
    "phòng trừ rỉ sắt trên lá cà phê",
    "thời điểm trồng tái canh cà phê",
]

GREETING_PROMPTS = ["xin chào", "hello", "chào bạn"]
THANKS_PROMPTS = ["cảm ơn", "ok cảm ơn"]
GOODBYE_PROMPTS = ["tạm biệt", "bye"]
CAPABILITY_PROMPTS = ["bạn làm được gì", "Nông Trí AI là gì", "bạn là ai"]


@pytest.mark.parametrize("prompt", SOCIAL_INVITATION_PROMPTS)
def test_social_invitation_caught_before_rag(prompt):
    """Câu xã giao có nhắc tới crop phải bị catch sớm để không gọi RAG/LLM."""
    response = basic_chat_response(prompt)
    assert response is not None, f"social prompt leaked to RAG: {prompt!r}"
    assert "trợ lý" in response["answer"]
    assert response["confidence_level"] == "cao"


@pytest.mark.parametrize("prompt", AGRI_PROMPTS_SHOULD_PASS_TO_RAG)
def test_agriculture_questions_still_pass_through(prompt):
    """Câu hỏi nông nghiệp thật phải để None để router gọi RAG như cũ."""
    assert basic_chat_response(prompt) is None, (
        f"agri prompt was incorrectly intercepted as basic intent: {prompt!r}"
    )


@pytest.mark.parametrize("prompt", GREETING_PROMPTS)
def test_greeting_unchanged(prompt):
    response = basic_chat_response(prompt)
    assert response is not None
    assert "Nông Trí AI" in response["answer"]


@pytest.mark.parametrize("prompt", THANKS_PROMPTS)
def test_thanks_unchanged(prompt):
    response = basic_chat_response(prompt)
    assert response is not None
    assert "vui được hỗ trợ" in response["answer"]


@pytest.mark.parametrize("prompt", GOODBYE_PROMPTS)
def test_goodbye_unchanged(prompt):
    response = basic_chat_response(prompt)
    assert response is not None
    assert "Tạm biệt" in response["answer"]


@pytest.mark.parametrize("prompt", CAPABILITY_PROMPTS)
def test_capability_unchanged(prompt):
    response = basic_chat_response(prompt)
    assert response is not None
    assert "trợ lý" in response["answer"]
