"""Compare the course RAG answers with unguided answers to five lab questions.

``questions.json`` is a JSON array of five
objects. Each object has a ``question`` string and a ``type`` of
``single_page``, ``two_page``, or ``unanswerable``. Use each type three, one,
and one times respectively. This runner prints the evidence and both answers;
the student records factual pass/fail judgments in CHECKS.md.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import course_rag


QUESTIONS_PATH = Path(__file__).with_name("questions.json")
EXPECTED_TYPES = Counter({"single_page": 3, "two_page": 1, "unanswerable": 1})


class QuestionsError(ValueError):
    """The question file is missing or does not match the lab format."""


def load_questions(path: Path) -> list[dict[str, str]]:
    """Validate the five evaluation cases before making any API calls."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise QuestionsError(
            f"No question file at {path}. Write questions.json with five "
            "objects containing question and type."
        ) from None
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise QuestionsError(f"Could not read valid JSON questions from {path}.") from None

    if not isinstance(data, list) or len(data) != 5:
        raise QuestionsError("questions.json must be a JSON array of exactly five objects.")

    cases: list[dict[str, str]] = []
    for number, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise QuestionsError(f"Question {number} must be an object.")
        question = item.get("question")
        case_type = item.get("type")
        if not isinstance(question, str) or not question.strip():
            raise QuestionsError(f"Question {number} must have nonblank question text.")
        if not isinstance(case_type, str) or case_type not in EXPECTED_TYPES:
            raise QuestionsError(
                f"Question {number} needs type single_page, two_page, or unanswerable."
            )
        cases.append({"question": question.strip(), "type": case_type})

    if Counter(case["type"] for case in cases) != EXPECTED_TYPES:
        raise QuestionsError(
            "Use three single_page, one two_page, and one unanswerable question."
        )
    return cases


def _error_label(exc: Exception) -> str:
    """Keep unexpected exception messages (which may include credentials) private."""
    if isinstance(exc, course_rag.RAGError):
        return str(exc)
    return f"Unexpected {type(exc).__name__}; inspect the local code or API."


def run_evaluation(cases: list[dict[str, str]]) -> bool:
    """Run both modes for every case; return whether every API call completed."""
    model = course_rag._model(None)
    print(f"Chat model for both modes: {model}", flush=True)
    all_completed = True
    for number, case in enumerate(cases, start=1):
        question = case["question"]
        print(f"\n{'=' * 72}")
        print(f"Case {number}/5 ({case['type']})")
        print(f"Question: {question}", flush=True)

        print("\nWITH RETRIEVAL — five excerpts and scores:", flush=True)
        try:
            result = course_rag.answer_question(
                question, chat_model=model, print_evidence=True
            )
        except Exception as exc:
            all_completed = False
            print(f"With retrieval ERROR: {_error_label(exc)}", flush=True)
        else:
            print(f"With retrieval ANSWER: {result.answer}")
            print(
                "With retrieval CITATIONS: "
                + (", ".join(result.citations) if result.citations else "none")
            )
            print("Top-five sources:")
            for rank, hit in enumerate(result.retrieved, start=1):
                print(
                    f"  {rank}. {hit.source}:{hit.start_line}-{hit.end_line} "
                    f"score={hit.score:.6f}"
                )

        print("\nWITHOUT RETRIEVAL — question only, no excerpts:", flush=True)
        try:
            baseline = course_rag.answer_without_retrieval(
                question, chat_model=model
            )
        except Exception as exc:
            all_completed = False
            print(f"Without retrieval ERROR: {_error_label(exc)}", flush=True)
        else:
            print(f"Without retrieval ANSWER: {baseline}", flush=True)

    print(f"\n{'=' * 72}")
    print("Review each answer against the course pages and record pass/fail in CHECKS.md.")
    return all_completed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--questions",
        type=Path,
        default=QUESTIONS_PATH,
        help="Path to the five-question JSON file (default: questions.json).",
    )
    args = parser.parse_args()
    try:
        cases = load_questions(args.questions)
        completed = run_evaluation(cases)
    except (QuestionsError, course_rag.RAGError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
