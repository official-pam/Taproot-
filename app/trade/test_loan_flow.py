"""Taproot loan request flow: summary, separate consent, stop sharing."""

import asyncio
from unittest.mock import AsyncMock, patch

from app.credit.demo import ngozi
from app.schemas.memory import User
from app.trade import flow


def _user() -> User:
    u = User(phone="2348000000009")
    u.role = "trader"
    u.language = "english"
    u.consent_status = "granted"
    return u


def _texts(reply) -> str:
    return " ".join(m["text"]["body"] for m in reply.messages if m.get("type") == "text")


def test_loan_summary_then_consent_buttons():
    entries, _ = ngozi()
    user = _user()
    with patch.object(flow.storage, "trade_entries", AsyncMock(return_value=entries)), \
         patch.object(flow.storage, "save_user", AsyncMock()):
        reply = asyncio.run(flow.handle_choice(user, "trade_loan"))
    text = _texts(reply)
    assert "Zenith Bank makes the final decision" in text
    assert "permission" in text and "stop sharing" in text
    assert reply.messages[-1]["interactive"]["action"]["buttons"][0]["reply"]["id"] == "loan_share_yes"
    assert user.flow_data["awaiting"] == "loan_share"


def test_consent_recorded_with_version_and_channel():
    user = _user()
    user.flow, user.flow_data = flow.FLOW, {"awaiting": "loan_share"}
    grant = AsyncMock()
    with patch.object(flow.storage, "credit_consent_grant", grant), \
         patch.object(flow.storage, "save_user", AsyncMock()):
        reply = asyncio.run(flow.continue_flow(user, "yes"))
    assert "shared with Zenith Bank" in _texts(reply)
    kwargs = grant.call_args.kwargs
    assert kwargs["partner"] == "Zenith Bank Plc" and kwargs["version"] == "loan-share-v1"
    assert kwargs["channel"] == "voice" and kwargs["language"] == "english"


def test_decline_shares_nothing():
    user = _user()
    user.flow, user.flow_data = flow.FLOW, {"awaiting": "loan_share"}
    grant = AsyncMock()
    with patch.object(flow.storage, "credit_consent_grant", grant), \
         patch.object(flow.storage, "save_user", AsyncMock()):
        reply = asyncio.run(flow.handle_choice(user, "loan_share_no"))
    grant.assert_not_called()
    assert "Nothing has been shared" in _texts(reply)


def test_stop_sharing_revokes():
    user = _user()
    with patch.object(flow.storage, "credit_consent_revoke", AsyncMock(return_value=1)), \
         patch.object(flow.storage, "save_user", AsyncMock()):
        assert flow.looks_like_trade("please stop sharing my record", user)
        reply = asyncio.run(flow.start(user, "please stop sharing my record"))
    assert "stopped sharing" in _texts(reply)


def test_thin_record_gets_tip_not_consent():
    user = _user()
    with patch.object(flow.storage, "trade_entries", AsyncMock(return_value=[])), \
         patch.object(flow.storage, "save_user", AsyncMock()):
        reply = asyncio.run(flow.handle_choice(user, "trade_loan"))
    assert "not ready for a loan yet" in _texts(reply)
    assert not any(m.get("type") == "interactive" for m in reply.messages)
