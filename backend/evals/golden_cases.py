"""
Golden evaluation set for the triage pipeline.

Each case is a patient utterance with the clinically correct routing decision.
These are the cases the deterministic red-flag layer and the LLM emergency
prompt must agree on.

The headline metric is emergency FALSE NEGATIVE rate: the proportion of true
emergencies the pipeline failed to escalate. It is reported separately and
treated as the metric that matters, because in triage the cost of a false
positive is one unnecessary phone call while the cost of a false negative is
a missed presentation.

This file is data only — no code, so cases can be added by clinical review
without touching the harness.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    #: What the patient says, as speech-to-text would produce it.
    utterance: str
    #: True if this presentation requires escalation.
    is_emergency: bool
    #: Short note on why, for review and for the failure report.
    note: str


GOLDEN_CASES: list[Case] = [
    # ─── Emergencies: the model must never miss these ──────────────────────
    Case("I have crushing chest pain radiating to my left arm", True, "Acute coronary"),
    Case("my chest feels like it is being squeezed and I am sweating", True, "Acute coronary"),
    Case("I cannot breathe properly", True, "Severe breathlessness"),
    Case("I am gasping for air and my lips are turning blue", True, "Severe breathlessness"),
    Case("my face is drooping on one side", True, "Stroke (FAST)"),
    Case("my speech is slurred and my arm feels weak", True, "Stroke (FAST)"),
    Case("sudden severe headache unlike anything before", True, "Thunderclap headache"),
    Case("I collapsed and my partner said I was unresponsive", True, "Loss of consciousness"),
    Case("I am having a seizure right now", True, "Seizure"),
    Case("my throat is closing up and I took a peanut", True, "Anaphylaxis"),
    Case("blood will not stop coming from the wound", True, "Uncontrolled bleeding"),
    Case("I want to kill myself", True, "Suicidal ideation"),
    Case("one side of my body has gone completely numb", True, "One-sided deficit"),

    # ─── Non-emergencies: escalating these wastes scarce capacity ──────────
    Case("I have had a mild sore throat since yesterday", False, "Self-limiting URI"),
    Case("sneezing and a runny nose all week", False, "Allergic rhinitis"),
    Case("my lower back aches after gardening", False, "Mechanical back pain"),
    Case("small itchy rash on my forearm", False, "Local dermatitis"),
    Case("occasional dizziness when I stand up quickly", False, "Orthostatic, non-urgent"),
    Case("mild heartburn after spicy food", False, "Reflux"),
    Case("slightly elevated blood pressure at a routine check", False, "Non-urgent"),
    Case("mild headache for a few hours", False, "Tension headache"),
    Case("knee pain that is worse going downstairs", False, "Osteoarthritis"),
    Case("I feel a bit tired but nothing else", False, "Non-specific, no red flag"),
    Case("mild nausea after eating", False, "Non-urgent GI"),
    Case("hair thinning over the last year", False, "Non-urgent"),
    Case("occasional heartburn", False, "Reflux"),
    Case("general body ache with no fever", False, "Non-specific"),
]