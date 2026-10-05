# Week 4: Ask the course

A local question-answering page for CPSC 415. It embeds the course's Markdown
pages, retrieves the five closest excerpts for a question, and asks
`openai/gpt-6-luna` to answer from those excerpts with file and line citations.
It uses `openai/text-embedding-3-small` for both document and question
embeddings. The page and server output show every retrieved excerpt and its
cosine score. When the evidence is insufficient, the answer is exactly
`I can't find that in the course documents.`

## Setup and use

Use Python 3.10 and [uv](https://docs.astral.sh/uv/). Place the course checkout
beside this repository, at `../ai-integration-course`. If it is absent, run
`git clone https://github.com/kousen/ai-integration-course.git ../ai-integration-course`
from this repository. The indexer reads only that checkout's `syllabus.md`,
`assignments/**/*.md`, and `weeks/01` through `weeks/03` Markdown files. It
does not index Week 4 or copy the pages into this repository.

Put your OpenRouter key in an ignored local `.env` file as
`OPENROUTER_API_KEY=your-key`. From this repository, run:

```sh
uv sync --python 3.10
set -a; source .env; set +a
uv run python index_course.py
uv run python app.py
```

Open <http://127.0.0.1:8924/> and enter a question. The server binds only to
`127.0.0.1`; set `PORT` to change the port. `OPENROUTER_API_KEY` is required
for indexing and answering. `CHAT_MODEL` optionally overrides the default
`openai/gpt-6-luna` answer model. The generated `index.json` and `.env` are
ignored by Git. Rebuild the index after the sibling course pages change.

To repeat the five-case comparison with the same answer model in both modes,
run `uv run python eval_questions.py`. It prints the five scored retrieval hits
and cited answer, then asks the same question with no excerpts in the prompt.
The recorded results and judgments are in `CHECKS.md`.

## Five questions and results

The agent drafted these questions at the user's explicit request. They are
recorded in `questions.json`; they are **not claimed as student-authored**.

| # | Question | What it checks | With retrieval | Without retrieval |
|---:|---|---|---|---|
| 1 | When is the Week 4 Ask the course assignment due on Moodle? | Single-page due date in the assignment sheet. | Pass: October 19, 2026, 1:30 PM, cited. | Fail: asks for the course page. |
| 2 | What percentage of the course grade is the Individual Portfolio: AI-Enabled Profile Site? | Single-page grade weight. | Pass: 25%, cited. | Fail: cannot supply the grade weight. |
| 3 | In the Week 3 lab intent, what three fields must the classifier print in JSON? | Single-page lab instruction. | Pass: category, urgency, one-sentence reason, cited. | Fail: invents different fields. |
| 4 | When was the Week 3 structured-output assignment due, and how many 24-hour late days does the syllabus grant each student? | Combines an assignment page and the syllabus. | Pass: October 5, 2026, 1:30 PM and three late days, with both citations. | Fail: asks for the missing pages. |
| 5 | What color is Prof. Kousen's office door? | Unanswerable detail; requires the exact refusal. | Pass: exact refusal, no citation. | Fail: does not use the required refusal sentence. |

The recorded evaluation passed **5/5 with retrieval** and **0/5 without
retrieval under the task's expected-answer criteria**. The baseline
did avoid guessing the door color, but did not give the required sentence; its
other answers either lacked the course facts or invented fields. Retrieval
provided the course evidence and citations, while the no-excerpt baseline
had no way to verify those details.

## Stale Xiaomi MiMo pages

For “Which Xiaomi MiMo model does this course use as the fallback or second
model?”, retrieval found both `weeks/01/setup.md:14-20` and
`weeks/03/lab.md:78-82`. The older Week 1 setup calls `xiaomi/mimo-v2.5` an
instructor fallback; the newer Week 3 lab calls `xiaomi/mimo-v2.6-flash` its
second model. The first answer mentioned only Week 3 despite retrieving both.
After a general instruction to report differing names with their page or week
contexts, the answer reported and cited both. One possible improvement is to
store each source line's Git last-change date and prefer newer evidence when
two pages make competing claims, while still showing both. That recency change
is not implemented. `CHECKS.md` records the answer, five hit sources and
scores, and the dates.

## A line I can explain

In `course_rag.py:209`,
`sum(a * b for a, b in zip(chunk.embedding, question_vector))` computes the
dot product of a document chunk and the question embedding. The next line
divides by their lengths to get cosine similarity; the highest-scoring five
chunks are sent to the answer model. A high score makes a chunk relevant, but
the answer still needs explicit support in its text.
