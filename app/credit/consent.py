"""The second consent: sharing a trader's business record with the bank.

Onboarding consent covers storing chats and the phone number. Sharing the
sales record with a lender is a different purpose, so it gets its own
consent, asked only when the trader asks for a loan. It names the bank and
the purpose, is read out in the trader's language, can be withdrawn at any
time by saying "stop sharing", and is stored with a timestamp and the wording
version (see ``credit_consents`` in app/storage/models.py).

The English text below is translated and voiced by the reply pipeline, like
every other reply. Bump VERSION whenever the wording changes.
"""

PARTNER = "Zenith Bank Plc"
PURPOSE = "loan_assessment"
VERSION = "loan-share-v1"

ASK = (
    "Before I send anything, I need your permission. "
    "If you say yes, I will share your sales record with Zenith Bank so they can look at you for a loan. "
    "This means your sales, costs, profit and stock, and your name and phone number. "
    "Zenith Bank will use it only to assess your loan. "
    "You can stop sharing at any time by saying: stop sharing. "
    "Do you agree?"
)
ASK_CARD = (
    "Share your sales record with Zenith Bank Plc?\n"
    "• What: sales, costs, profit, stock, name, phone number\n"
    "• Why: only to assess you for a loan\n"
    "• Stop any time: say \"stop sharing\""
)
GRANTED = "Thank you. Your record is now shared with Zenith Bank. A loan officer can now review it."
DECLINED = "No problem. Nothing has been shared. Your sales book stays private to you."
REVOKED = "Done. I have stopped sharing your record with Zenith Bank."
NOTHING_TO_REVOKE = "You are not sharing your record with anyone."

STOP_PHRASES = ("stop sharing", "stop share", "cancel sharing", "withdraw consent")
