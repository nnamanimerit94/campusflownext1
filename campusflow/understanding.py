"""Local, deterministic Engineering Understanding Check (not AI grading)."""

from collections.abc import Callable

QUESTIONS: tuple[tuple[str, str], ...] = (
    (
        "Why does CampusFlow validate the complete ticket store before mutation?",
        "Expected: reject corrupt records and preserve the entire in-memory store on failure.",
    ),
    (
        "How does affected_users change priority when the count reaches 10?",
        "Expected: escalate one tier: low to medium, medium to high, high to critical.",
    ),
    (
        "Which status transitions are allowed, and how is a ticket reopened?",
        "Expected: open -> in_progress -> resolved -> closed; reopen resolved/closed "
        "using reopen_ticket, not transition_ticket.",
    ),
    (
        "Why does the JSON saver use a temporary file and os.replace?",
        "Expected: validate, flush and fsync a sibling temporary file before atomic "
        "replacement; failed pre-replace writes must preserve the old file.",
    ),
    (
        "How do search filters combine, and what does the report count?",
        "Expected: search uses casefolded substring matching and AND filters; "
        "reports count current statuses with zero-filled enum buckets.",
    ),
)


def run_check(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], object] = print,
) -> None:
    """Ask one practice question at a time, then reveal reference guidance.

    Answers are not graded. No filesystem access or ticket mutations occur.
    """
    output_fn("CampusFlow Next Engineering Understanding Check")
    output_fn("Practice only: reference guidance is shown; answers are not AI-graded.")
    for number, (question, guidance) in enumerate(QUESTIONS, start=1):
        output_fn(f"Question {number}/{len(QUESTIONS)}: {question}")
        try:
            answer = input_fn("Your answer (or 'quit' to exit): ")
        except (EOFError, KeyboardInterrupt):
            output_fn("Check ended without grading.")
            return
        if not isinstance(answer, str):
            raise TypeError("input_fn must return text")
        if answer.strip().casefold() in {"quit", "exit"}:
            output_fn("Check ended without grading.")
            return
        output_fn(guidance)
    output_fn("Practice complete. Compare your responses with the guidance; no score assigned.")
