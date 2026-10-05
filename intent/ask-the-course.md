# Intent: Ask the course

## Goal
Build a local web app that answers questions about CPSC 415 from the course's
own Markdown pages. Each answer cites the pages it used. When those pages do
not support an answer, the app says exactly: "I can't find that in the course
documents."

## Who it is for
A CPSC 415 student checking course requirements and policies without searching
each page by hand. The student can inspect the source pages behind an answer.

## Constraints
- Use Python 3.10 and uv for a local web app and its index-building command.
- Use cost-conscious OpenRouter models. Keep the API key in the server
  environment, never in browser code or the repository.
- Index only `../ai-integration-course/syllabus.md`, `assignments/`, and
  `weeks/01` through `weeks/03`. Exclude Week 4 and do not copy course pages
  into this repository.
- Print the retrieved chunks and their scores in the server output for every
  answer, and show the same evidence on the page.
- Complete the Week 4 lab artifacts and submission by October 19, 2026,
  1:30 PM.

## Not in scope
Hosting the app on the public internet, answering from the model's general
knowledge, or automatically resolving disagreements between course pages.

## Success looks like
1. A student can build the index, open the local page, ask a course question,
   and see an answer with page citations and retrieved chunks with scores.
2. A question unsupported by the indexed pages returns the exact refusal
   sentence above.
3. The five-question evaluation records results with and without retrieval,
   and the stale-page exercise records which conflicting sources were cited.

## Open questions
None at the intent level. Model and library choices belong in the spec.

**Approved by:** Ralston Raphael, October 5, 2026 (delegated in chat)
