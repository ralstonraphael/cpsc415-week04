# Checks

## Five-question evaluation

The user explicitly asked the agent to draft the five questions in
`questions.json`. The final complete run was on October 5, 2026 with
`openai/gpt-6-luna` in both modes. With retrieval, the question was embedded
with `openai/text-embedding-3-small`, the five closest indexed excerpts were
sent to Luna, and all five chunks and scores were printed. Without retrieval,
Luna got the question alone, without excerpts or a grounding instruction.
I checked each answer against the source pages.

**Result:** With retrieval, all **5/5** met the task criterion. Without
retrieval, **0/5** did: it abstained on four, and gave invented field names on
one. A safe abstention is preferable to a guess, but it does not answer the
four answerable course questions; the unanswerable case did not use the exact
course-document refusal required by this lab.

1. **Week 4 due date — single page.** Expected Monday, October 19, 2026,
   1:30 PM on Moodle from `assignments/week04-rag-plan.md:1-7`.
   - With retrieval: “The Week 4 Ask the course assignment is due Monday,
     October 19, 2026, at 1:30 PM on Moodle.
     [assignments/week04-rag-plan.md:1-7]” **Pass.**
   - Without retrieval: “I can’t access your Moodle course page. Which
     course is this for? If you share the assignment details or a screenshot,
     I can help find the due date.” **No answer.**
2. **Portfolio grade weight — single page.** Expected 25% from
   `syllabus.md:94-103`.
   - With retrieval: “The Individual Portfolio: AI-Enabled Profile Site is
     25% of the course grade. [syllabus.md:94-103]” **Pass.**
   - Without retrieval: “I don’t have the course grading breakdown. Share
     the syllabus or grade table, and I can find the percentage.” **No
     answer.**
3. **Week 3 JSON fields — single page.** Expected category, urgency, and a
   one-sentence reason from `weeks/03/lab.md:19-31`.
   - With retrieval: “The three fields are category, urgency, and a
     one-sentence reason. [weeks/03/lab.md:19-31]” **Pass.**
   - Without retrieval: “The classifier must print `intent`, `confidence`,
     and `entities` in JSON.” **Fail: invented fields.** This mode had no
     retrieved chunks or citations by design.
4. **Week 3 due date plus late days — two pages.** Expected Monday, October
   5, 2026, 1:30 PM from `assignments/week03-structured-output.md:1-7` and
   three 24-hour late days from `syllabus.md:122-130`.
   - With retrieval: “The Week 3 structured-output assignment was due
     Monday, October 5, 2026, at 1:30 PM on Moodle
     [assignments/week03-structured-output.md:1-7]. Each student gets 3
     late days, usable in 24-hour increments [syllabus.md:122-130].”
     **Pass.**
   - Without retrieval: “I don’t have the Week 3 assignment details or
     syllabus here. Please share them, and I can identify the due date and
     the number of 24-hour late days.” **No answer.**
5. **Office-door color — unanswerable.** The indexed pages do not specify
   it. Expected `I can't find that in the course documents.`
   - With retrieval: `I can't find that in the course documents.` **Pass;
     no citation.**
   - Without retrieval: “I can’t tell from the information provided. If you
     share the photo or source, I can identify the door’s color.” **Safe
     abstention, but not the required refusal.**

The first draft of case 3 asked, “What three JSON fields does the Week 3
support-message classifier return?” Its answer existed in the corpus, but the
relevant `weeks/03/lab.md:19-31` chunk ranked **11th**, outside the five
excerpts, so the grounded answer refused. This was a retrieval failure, not a
missing fact. The five chunks printed for that failed draft were:

| Rank | Source | Cosine score |
|---:|---|---:|
| 1 | `weeks/03/lab.md:1-5` | 0.473744 |
| 2 | `weeks/03/README.md:1-13` | 0.444923 |
| 3 | `weeks/03/setup.md:19-21` | 0.443904 |
| 4 | `assignments/week03-structured-output.md:21-28` | 0.440034 |
| 5 | `weeks/02/README.md:42-44` | 0.424136 |

I made the question's reference to the Week 3 *lab intent* more precise. The
supporting chunk then ranked fourth, and the final five-case run passed.
This wording sensitivity remains a retrieval limitation; the check does not
claim that every paraphrase will work. In an intermediate run, the unguided
case 3 API call returned no text with a 500-token completion limit. The
runner reported the error and continued. After raising that limit to 1,200,
the full final run completed and exposed its incorrect baseline answer.

## Stale Xiaomi MiMo page

Question: **Which Xiaomi MiMo model does this course use as the fallback or
second model?**

The first run on October 5 retrieved both model references, but the answer
mentioned only the Week 3 second model: “The Week 3 lab’s second model is
xiaomi/mimo-v2.6-flash. [weeks/03/lab.md:78-82]” This showed that retrieving a
conflicting page does not guarantee the generator will disclose it. I made the
general conflict instruction more explicit and reran the same question. The
second answer was: “Week 1’s setup guide names xiaomi/mimo-v2.5 as the
instructor fallback [weeks/01/setup.md:14-20]. Week 3’s lab uses
xiaomi/mimo-v2.6-flash as the second model [weeks/03/lab.md:78-82].” Both
citations were validated against the retrieved chunks.

| Rank | Retrieved source | Cosine score |
|---:|---|---:|
| 1 | `weeks/03/lab.md:78-82` | 0.510553 |
| 2 | `syllabus.md:82-86` | 0.403208 |
| 3 | `weeks/02/lab.md:101-105` | 0.390685 |
| 4 | `weeks/01/setup.md:14-20` | 0.382677 |
| 5 | `weeks/02/setup.md:32-42` | 0.370430 |

The Week 1 line calls v2.5 an instructor fallback; the Week 3 line calls
v2.6-flash a second model. Those are different weeks and roles, so the answer
should retain both contexts rather than collapse them into one current model.
`git blame` dates the Week 1 model line to September 9 and the Week 3 line to
September 28. A possible improvement is to save a last-change date per chunk
and, when two retrieved chunks disagree about the same policy or model, show
both while giving the newer line more weight. This lab records the issue and
does not implement that ranking change.
