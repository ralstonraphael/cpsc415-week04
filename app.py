"""Local browser interface for asking the indexed course documents."""

from __future__ import annotations

import os

from flask import Flask, render_template, request

from course_rag import RAGError, answer_question


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    question = ""
    result = None
    error = None

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if not question:
            error = "Enter a question before asking the course."
        else:
            try:
                result = answer_question(question)
            except RAGError as exc:
                error = str(exc)

    return render_template(
        "index.html", question=question, result=result, error=error
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8924")), debug=False)
