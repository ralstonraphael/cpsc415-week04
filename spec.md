# Spec: Ask the course

## Intent
Implements `intent/ask-the-course.md`.

## Components

### Indexer
- **What it does:** Reads only the allowed course Markdown files from the
  sibling `../ai-integration-course` checkout, splits them into overlapping
  chunks, embeds each chunk, and saves a rebuildable local JSON index.
- **Language:** Python 3.10. **Why:** It is the chosen lab language and keeps
  file handling, embedding calls, and the web app in one environment. Java
  would require more setup for this short lab.
- **Model:** `openai/text-embedding-3-small` through OpenRouter. **Why:** The
  Week 4 setup uses this 1,536-dimensional model, and its listed price is
  $0.02 per million input tokens. A free embedding model is an alternative,
  but using the course example reduces setup uncertainty. The asker must use
  this same model for questions. [Model details](https://openrouter.ai/openai/text-embedding-3-small)
- **Interfaces:** `uv run python index_course.py` reads `syllabus.md`, every
  Markdown file under `assignments/`, and Markdown files under `weeks/01`,
  `weeks/02`, and `weeks/03`. It writes `index.json` containing the embedding
  model name and, for each chunk, its text, vector, relative path, heading,
  and starting and ending line numbers. It prints file and chunk counts.
  `index.json` is ignored by Git and can be rebuilt from the sibling checkout.
- **Chunking:** Split at headings and paragraph boundaries into roughly
  200–250 words per chunk with about 40 words of overlap. Keep a heading with
  its text and preserve the source line range. This aims to keep a policy or
  lab step together while avoiding whole-page prompts.
- **Dependencies:** `openai` for OpenRouter-compatible embedding and chat API
  calls, including authentication, timeouts, and response parsing; `uv` for a
  repeatable Python environment. Markdown parsing and cosine similarity use
  the Python standard library, so no RAG framework is needed.

### Asker
- **What it does:** Serves a local question form, embeds each question,
  ranks stored chunks by cosine similarity, and asks a chat model to answer
  only from the retrieved excerpts. It shows the answer, citations, chunks,
  and scores on the page and prints the same retrieval evidence to the server
  output.
- **Language:** Python 3.10. **Why:** The web app can load the indexer's JSON
  directly and share its embedding and retrieval functions. A Java server
  would add a second build environment without helping this lab.
- **Model:** `openai/gpt-6-luna` through OpenRouter. **Why:** It is a low-cost
  answer model (listed at $0.10 per million input tokens and $0.50 per million
  output tokens) suitable for short cited answers. The stronger comparison
  model is `openai/gpt-6.1-sol` (listed at $2/$10 per million). On October 5,
  both models answered the same real two-page question about the Week 3 due
  date and semester late days correctly, citing both excerpts. Luna took 1.8
  seconds and cost $0.0000486; Sol took 3.35 seconds and cost $0.001022.
  Luna met this task at about one-twentieth the cost, so it is the default.
  An earlier Luna call with longer excerpts timed out, so the app must handle
  timeouts clearly. [Luna](https://openrouter.ai/openai/gpt-6-luna) ·
  [Sol](https://openrouter.ai/openai/gpt-6.1-sol)
- **Interfaces:** `uv run python app.py` binds to `127.0.0.1` and serves a
  local page with a question field and a result view. The backend reads
  `OPENROUTER_API_KEY`, `index.json`, and optional `CHAT_MODEL`. A separate
  `uv run python eval_questions.py` reads `questions.json` and
  runs each question with retrieval and as an unguided baseline: the same
  answer model receives the question without excerpts or the instruction to
  answer only from excerpts. This isolates the effect of retrieval. Neither
  the page nor the repository contains the API key.
- **Dependencies:** `flask` for the local form and result page; `openai` for
  OpenRouter-compatible question embeddings and chat completions; `uv` for
  running the app and evaluation with the project's declared dependencies.

## Behavior
1. Index only `../ai-integration-course/syllabus.md`, `assignments/**/*.md`,
   and `weeks/{01,02,03}/**/*.md`. Never read `weeks/04` or copy source pages
   into this repository. Report a nonzero chunk count and the number of files.
2. Store each chunk's source path, heading, line range, text, and vector in
   `index.json`. Store the embedding model and reject an index whose model or
   vector dimension differs from the question embedding.
3. For a nonblank question, embed it with the indexer's model, rank chunks by
  cosine similarity, and give the top five to the answer model. Print all five
   chunks with numeric scores and sources for every processed question,
   including one that ends in a refusal; show them on the local page as well.
4. Tell the answer model to use only those excerpts, cite its supporting
   source path and line range, and decline to answer if the excerpts do not
   establish the answer. Reject a model citation that does not refer to one
   of the retrieved chunks.
5. If the documents do not support an answer, show exactly `I can't find that
   in the course documents.` and do not present an unsupported citation.
6. `questions.json` has five cases: three answered in one
   place, one requiring two pages, and one absent from the corpus. The eval
   runs all five with retrieval and as the unguided baseline just described,
   records both outputs and retrieved sources, and leaves pass/fail judgments
   for `CHECKS.md`.
7. The stale Xiaomi MiMo question runs through the same asker. Record its
   answer and cited chunks in `CHECKS.md`; a recency fix may be proposed but
   is not required to be implemented.
8. A blank question, missing index, missing key, unavailable API, or malformed
   API response yields a clear local error without exposing the key.

## Failure handling
The indexer fails with a clear path if the sibling corpus is missing or no
Markdown files are found. API calls use bounded timeouts and report status or
network errors without credentials. The asker refuses unsupported answers and
invalid citations. A similarity score alone does not prove an answer exists;
the five-question evaluation checks the refusal behavior.

## Cost estimate
The allowed corpus has 16 Markdown files and about 14,430 words. At the
currently listed embedding rate of $0.02 per million tokens, one index build
is well under $0.01. At an estimated 2,000 input and 250 output tokens per
answer, Luna costs about $0.00033 per answer; 100 questions would be about
$0.03, plus query embeddings, for a semester of roughly 100 questions. One
Sol answer at the same estimated size would cost about $0.0065. The smaller
live comparison used 136 input tokens and cost $0.0000486 on Luna versus
$0.001022 on Sol. Actual cost depends on chunking, prompts, usage, and current
model prices; check OpenRouter's usage totals during evaluation.

## Out of scope
Public hosting, authentication, indexing Week 4 pages, answering from general
model knowledge, automatically resolving stale-page conflicts, and a managed
vector database.

## Later direction
After the spec and plan were approved, the user asked the agent to draft the
five evaluation questions. The author is disclosed in `README.md` and
`CHECKS.md`; the approved spec commit remains in Git history.
