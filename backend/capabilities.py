"""
Capability grounding.

The model must never describe what the system can do. Asked to book an
appointment it replied "I can't book it directly here, but please call your
clinic" — while the application books appointments in-app.

That is a hallucination about system state, which is the same failure class as
the IDOR: the model asserting something it cannot observe. The fix is not a
better prompt, it is computing the facts and telling the model what they are.
"""

#: Fixed, true statements about what this assistant is. Anything not listed
#: here is not something the model should claim.
BASE_CAPABILITIES = [
    "You can help a patient find and book appointments with doctors in this app.",
    "You do NOT diagnose, prescribe, or interpret test results.",
    "You cannot schedule anything by phone, and you cannot contact a clinic.",
    "You must never tell a patient to phone a clinic or use a patient portal "
    "to do something you can do here.",
    "You must never claim you cannot do something listed above.",
]


def build_capability_block(
    can_book: bool,
    available_doctors: int = 0,
    patient_signed_in: bool = False,
) -> str:
    """
    Describe the live system state for the prompt.

    Args:
        can_book: whether booking is currently possible at all.
        available_doctors: number of doctors with an open slot right now.
        patient_signed_in: whether a patient identity is attached to the session.

    Returns:
        A block of factual statements to embed in the guidance prompt.
    """
    lines = list(BASE_CAPABILITIES)

    if not patient_signed_in:
        lines.append(
            "This patient is not signed in, so they cannot book yet. "
            "Tell them to sign in to book, and do not say you are unable to book."
        )
    elif not can_book or available_doctors == 0:
        lines.append(
            "No doctors currently have an open slot, so booking is not possible "
            "right now. Say that no slots are open, not that you cannot book."
        )
    else:
        lines.append(
            f"{available_doctors} doctor(s) currently have an open slot and this "
            "patient is signed in, so booking IS possible right now."
        )

    return "\n".join(f"- {line}" for line in lines)