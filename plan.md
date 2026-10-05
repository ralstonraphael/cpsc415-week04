# Plan: Ask the course

Based on `spec.md` and `intent/ask-the-course.md`. Pause after each build step
and show its proof before starting the next. No program code is written until
this plan is approved and committed.

## Files to create or change
| File | Purpose |
|---|---|
| `pyproject.toml`, `uv.lock` | Declare Python 3.10, Flask, and the OpenAI SDK; lock the environment. |
| `.gitignore` | Ignore generated `index.json`; continue ignoring `.env`. |
| `index_course.py` | Walk exactly the allowed sibling files, chunk and embed them, save the JSON index, and print counts. |
| `course_rag.py` | Load the index, embed a question, cosine-rank chunks, print evidence and scores, and generate a cited answer or refusal. Share this between web and eval. |
| `app.py`, `templates/index.html` | Serve the question form and show answers, citations, chunks, scores, and local errors. |
| `questions.json` | Five questions written by the student: three single-page, one two-page, one unanswerable. |
| `eval_questions.py` | Run the five questions with retrieval and as an unguided, no-excerpt baseline using the same chat model. |
| `CHECKS.md` | Record both eval runs, failures and their chunk sources, and the stale-page finding. |
| `README.md` | Explain setup, environment, index and web commands, question purposes, results, stale page, and a ranking or refusal line. |
| `index.json` (generated, ignored) | Store chunk text, source metadata, model ID, and vectors; rebuild from the sibling course checkout. |

## Order of work
1. Add `pyproject.toml`, resolve dependencies with uv, and update `.gitignore`.
   Show the environment proof before continuing.
2. Build the indexer and its chunking in `index_course.py`. Embed only the
   allowed corpus and save `index.json`. Show file count, chunk count, vector
   size, chunk-length distribution, and source-path proof before continuing.
3. Build `course_rag.py`: load and validate the index, embed a question with
   the same model, rank by cosine similarity, send the top five excerpts to
   Luna, validate citations, and return a grounded answer or the exact refusal.
   If two retrieved excerpts disagree, instruct Luna to report both claims
   with both citations rather than silently select one. Show a real question's
   answer and printed evidence before continuing.
4. Build the Flask page and ask through it. Show the local page and server
   output for a cited answer and an unsupported question before continuing.
5. Have the student write the five `questions.json` cases. Build the eval
   runner, run both modes, and record pass/fail findings in `CHECKS.md`.
   Then ask the required Xiaomi MiMo stale-page question and record the answer,
   top-five chunks with scores, whether both conflicting pages were retrieved,
   and one possible recency fix. Show the records before continuing.
6. Finish `README.md`, inspect the repository for keys or copied source pages,
   commit the completed lab, tag `week04-submitted`, and push main and the tag.

## Risks
| Step | What could break and how to notice | Response |
|---|---|---|
| 1–2 | Wrong sibling path or a tiny index; the corpus should have 16 Markdown files. | Fail on missing roots and print file and chunk counts before any asker work. |
| 2 | Splitting a heading, table, or policy destroys context. | Target about 220 words with 40 words of overlap; allow up to 300 to keep a short table together, carry the heading into each chunk, and inspect lengths and source lines. |
| 2–3 | Index and question embeddings use different models or vector sizes. | Save the model ID and vector size, and reject mismatches. |
| 3–5 | A nearest chunk is irrelevant, or two pages disagree; similarity measures relevance rather than currentness. | Require support from cited excerpts, check citations against retrieved sources, tell the model to expose a retrieved conflict, and use the unanswerable eval. Record any stale-page answer without silently fixing it. |
| 3–5 | OpenRouter times out or returns an error; a Luna comparison call already timed out once. | Use bounded timeouts and surface a clear local error; never show the key. |
| 4–6 | The page omits retrieval evidence, or a secret/source copy enters Git. | Inspect the answer view and server output, confirm `.env` and `index.json` are ignored, and review staged files before push. |

## Proof
For API-backed steps, first export the key from the ignored local file with
`set -a; source .env; set +a`. The commands below never print the key.

1. `uv sync` exits successfully; `uv run python -c "import flask, openai"`
   exits 0. `git check-ignore .env index.json` prints both filenames.
2. `uv run python index_course.py` prints **16 files**, a plausible nonzero
   chunk count (roughly 60–110), and **1,536 dimensions**. Its source-path
   summary contains `syllabus.md`, `assignments/`, and `weeks/01`–`03`, with no
   `weeks/04` path. It prints minimum, median, and maximum chunk word counts;
   inspect sample chunks from the syllabus grading table and late-day policy
   for intact context, headings, and line ranges.
3. A direct call to `course_rag.answer_question` with "What percentage of the
   course grade is participation and labs?" prints five source paths, chunks,
   and numeric similarity scores; the answer says 15% and cites
   `syllabus.md`. "What color is Prof. Kousen's office door?" returns the
   exact refusal sentence while still printing its retrieved evidence.
4. `uv run python app.py` starts a server on `127.0.0.1`. Asking the same
   grading question in a browser shows 15%, a `syllabus.md` citation, five
   chunks, and scores; the server output also prints them. A blank question
   causes no API call.
5. `uv run python eval_questions.py` prints each of the five student-written
   questions with retrieval and without excerpts in the prompt. `CHECKS.md`
   records which passed, which failed and why, and the printed chunk sources
   for failures. For the Xiaomi question, record the answer and top-five source
   paths, line ranges, and scores; compare them with `weeks/01/setup.md:18`
   (`xiaomi/mimo-v2.5`) and `weeks/03/lab.md:80`
   (`xiaomi/mimo-v2.6-flash`). Note whether the newer page was retrieved and
   propose using each file's Git last-change date to prefer current evidence.
6. `README.md` contains every item in lab step 5. `git diff --check` passes;
   staged files contain no `.env`, key, copied course pages, or `index.json`.
   The final commit precedes `week04-submitted`, and both main and the tag are
   visible on GitHub.

## Questions asked before approval
1. **"Why that chunk size?"** About 220 words usually keeps one course
   policy or lab step together; 40 words of overlap reduces boundary misses.
   Five hits then fit in a modest answer prompt instead of sending whole
   pages. **Correction:** state the target, table exception, heading carryover,
   and chunk-length proof in steps 2 and the Risks and Proof sections.
2. **"What happens when pages disagree?"** Cosine similarity cannot tell
   which page is current. If both conflicting excerpts are retrieved, the
   answer should disclose both with citations. If only one is retrieved, the
   stale-page check must record the actual answer and missed source; no
   recency fix is implemented for this lab. **Correction:** add the conflict
   instruction to step 3 and a source-by-source Xiaomi check to step 5 and
   its proof, including a proposed Git-date rule.

## Subagents and parallel work
Read-only subagents checked the course corpus, current model details, and the
spec. Implementation and proof will be sequential to honor the lab's pause
after each step. No separate worktree is needed for this introductory lab.

**Approved by:** Ralston Raphael, October 5, 2026 (in chat)
