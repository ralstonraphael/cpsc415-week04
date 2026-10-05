"""Build a local embedding index from the first three weeks of course material.

Run with ``uv run python index_course.py`` after setting OPENROUTER_API_KEY.
The generated index.json is deliberately rebuildable and is ignored by Git.
"""

from __future__ import annotations

import json
import math
import os
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError, OpenAI


PROJECT_DIR = Path(__file__).resolve().parent
CORPUS_DIR = PROJECT_DIR.parent / "ai-integration-course"
INDEX_PATH = PROJECT_DIR / "index.json"
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EXPECTED_DIMENSION = 1536
TARGET_WORDS = 220
OVERLAP_WORDS = 40
TABLE_LIMIT_WORDS = 300
BATCH_SIZE = 64
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


@dataclass(frozen=True)
class Block:
    text: str
    start_line: int
    end_line: int
    kind: str
    heading: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def source_files() -> list[Path]:
    """Return exactly the permitted paths, without walking later weeks."""
    syllabus = CORPUS_DIR / "syllabus.md"
    roots = [CORPUS_DIR / "assignments"] + [
        CORPUS_DIR / "weeks" / week for week in ("01", "02", "03")
    ]
    missing = [str(path) for path in [syllabus, *roots] if not path.exists()]
    if missing:
        raise ValueError("Missing course source path(s): " + ", ".join(missing))
    paths = [syllabus]
    for root in roots:
        paths.extend(sorted(root.rglob("*.md")))
    if not paths or any(not path.is_file() for path in paths):
        raise ValueError("No readable Markdown files found in the allowed corpus.")
    return paths


def markdown_blocks(source: str) -> list[Block]:
    """Keep paragraph, list item, fenced code, and table boundaries with lines."""
    lines = source.splitlines()
    blocks: list[Block] = []
    heading = "Document"
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        start = index
        match = HEADING_RE.match(line)
        if match:
            heading = match.group(2).strip()
            blocks.append(Block(line, index + 1, index + 1, "heading", heading))
            index += 1
            continue
        if line.lstrip().startswith(("```", "~~~")):
            fence = line.lstrip()[:3]
            index += 1
            while index < len(lines):
                closing = lines[index].lstrip().startswith(fence)
                index += 1
                if closing:
                    break
            kind = "code"
        elif line.lstrip().startswith("|"):
            index += 1
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                index += 1
            kind = "table"
        elif LIST_RE.match(line):
            index += 1
            while index < len(lines) and lines[index].strip():
                following = lines[index]
                if HEADING_RE.match(following) or LIST_RE.match(following):
                    break
                if following.lstrip().startswith(("|", "```", "~~~")):
                    break
                index += 1
            kind = "list"
        else:
            index += 1
            while index < len(lines) and lines[index].strip():
                following = lines[index]
                if HEADING_RE.match(following) or LIST_RE.match(following):
                    break
                if following.lstrip().startswith(("|", "```", "~~~")):
                    break
                index += 1
            kind = "paragraph"
        blocks.append(
            Block("\n".join(lines[start:index]), start + 1, index, kind, heading)
        )
    return blocks


def split_oversize(block: Block) -> list[Block]:
    """Split only blocks larger than a full chunk, at source line boundaries."""
    limit = TABLE_LIMIT_WORDS if block.kind == "table" else TARGET_WORDS
    if block.word_count <= limit:
        return [block]
    source_lines = block.text.splitlines()
    pieces: list[Block] = []
    pending: list[str] = []
    start_line = block.start_line

    def flush(end_line: int) -> None:
        nonlocal pending, start_line
        if pending:
            pieces.append(
                Block("\n".join(pending), start_line, end_line, block.kind, block.heading)
            )
            pending = []

    for offset, line in enumerate(source_lines):
        line_number = block.start_line + offset
        words = line.split()
        if pending and len(" ".join(pending).split()) + len(words) > limit:
            flush(line_number - 1)
            start_line = line_number
        if len(words) > limit:
            for word_start in range(0, len(words), limit):
                if pending:
                    flush(line_number - 1)
                pieces.append(
                    Block(
                        " ".join(words[word_start : word_start + limit]),
                        line_number,
                        line_number,
                        block.kind,
                        block.heading,
                    )
                )
            start_line = line_number + 1
        else:
            if not pending:
                start_line = line_number
            pending.append(line)
    flush(block.end_line)
    return pieces


def overlap_tail(blocks: list[Block]) -> list[Block]:
    """Carry roughly 40 previous words into the next window.

    A whole table or code fence stays intact, so it is not copied as overlap.
    """
    tail: list[Block] = []
    remaining = OVERLAP_WORDS
    for block in reversed(blocks):
        if remaining <= 0 or block.kind in ("table", "code"):
            break
        words = block.text.split()
        if len(words) <= remaining:
            tail.append(block)
            remaining -= len(words)
        else:
            tail.append(
                Block(
                    " ".join(words[-remaining:]),
                    block.start_line,
                    block.end_line,
                    "overlap",
                    block.heading,
                )
            )
            remaining = 0
    return list(reversed(tail))


def chunk_file(path: Path) -> list[dict[str, object]]:
    blocks = [piece for block in markdown_blocks(path.read_text(encoding="utf-8"))
              for piece in split_oversize(block)]
    chunks: list[dict[str, object]] = []
    source = path.relative_to(CORPUS_DIR).as_posix()

    # A new heading starts a new section. Adjacent headings stay together so
    # a title followed immediately by a subheading never makes an empty chunk.
    sections: list[list[Block]] = []
    section: list[Block] = []
    has_content = False
    for block in blocks:
        if block.kind == "heading" and has_content:
            sections.append(section)
            section = []
            has_content = False
        section.append(block)
        has_content = has_content or block.kind != "heading"
    if has_content:
        sections.append(section)

    for section in sections:
        heading = next(block.heading for block in section if block.kind != "heading")
        window: list[Block] = []
        fresh: list[Block] = []

        def emit() -> None:
            if not fresh:
                return
            chunks.append(
                {
                    "id": f"{source}#{len(chunks) + 1}",
                    "source": source,
                    "heading": heading,
                    "start_line": min(block.start_line for block in window),
                    "end_line": max(block.end_line for block in window),
                    "text": "\n\n".join(block.text for block in window),
                }
            )

        for block in section:
            current_words = sum(item.word_count for item in window)
            fresh_words = sum(item.word_count for item in fresh)
            if window and fresh and current_words + block.word_count > TARGET_WORDS:
                allowed = TABLE_LIMIT_WORDS if block.kind == "table" else TARGET_WORDS + 35
                if fresh_words >= 100 or current_words + block.word_count > allowed:
                    previous = window.copy()
                    emit()
                    window = overlap_tail(previous)
                    fresh = []
                    # Never let the overlap itself crowd out the new block.
                    if sum(item.word_count for item in window) + block.word_count > allowed:
                        window = []
            window.append(block)
            fresh.append(block)
        emit()
    return chunks


def build_chunks(paths: list[Path]) -> list[dict[str, object]]:
    chunks = [chunk for path in paths for chunk in chunk_file(path)]
    if not chunks:
        raise ValueError("The allowed corpus produced no text chunks.")
    return chunks


def embed_chunks(chunks: list[dict[str, object]], key: str) -> int:
    client = OpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
        timeout=30.0,
        max_retries=2,
    )
    dimension = 0
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        inputs = [
            f"Source: {chunk['source']}\nSection: {chunk['heading']}\n\n{chunk['text']}"
            for chunk in batch
        ]
        try:
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=inputs)
        except APITimeoutError:
            raise RuntimeError("Embedding request timed out.") from None
        except APIConnectionError:
            raise RuntimeError("Could not connect to the embedding API.") from None
        except APIStatusError as exc:
            raise RuntimeError(f"Embedding API returned HTTP {exc.status_code}.") from None
        except APIError:
            raise RuntimeError("Embedding API returned an invalid response.") from None
        if not isinstance(response.data, list) or len(response.data) != len(batch):
            raise RuntimeError("Embedding API returned the wrong number of vectors.")
        for item in response.data:
            if not isinstance(item.index, int) or not 0 <= item.index < len(batch):
                raise RuntimeError("Embedding API returned an invalid item index.")
            vector = item.embedding
            if not isinstance(vector, list) or not vector or any(
                not isinstance(value, (float, int)) or not math.isfinite(value)
                for value in vector
            ):
                raise RuntimeError("Embedding API returned an empty or invalid vector.")
            if len(vector) != EXPECTED_DIMENSION or (dimension and len(vector) != dimension):
                raise RuntimeError("Embedding API returned inconsistent vector dimensions.")
            dimension = len(vector)
            batch[item.index]["embedding"] = vector
        if any("embedding" not in chunk for chunk in batch):
            raise RuntimeError("Embedding API omitted a vector.")
    return dimension


def main() -> int:
    try:
        paths = source_files()
        chunks = build_chunks(paths)
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise ValueError("Set OPENROUTER_API_KEY in the process environment before indexing.")
        dimension = embed_chunks(chunks, key)
        index = {
            "embedding_model": EMBEDDING_MODEL,
            "dimension": dimension,
            "source_root": "../ai-integration-course",
            "files": [path.relative_to(CORPUS_DIR).as_posix() for path in paths],
            "chunks": chunks,
        }
        INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Indexing failed: {exc}", file=sys.stderr)
        return 1

    counts = [len(str(chunk["text"]).split()) for chunk in chunks]
    print(f"Indexed {len(paths)} Markdown files into {len(chunks)} chunks.")
    print(f"Embedding model: {EMBEDDING_MODEL}; dimension: {dimension}")
    print("Indexed source files:")
    for path in paths:
        print(f"  {path.relative_to(CORPUS_DIR).as_posix()}")
    print(
        "Chunk words (min/median/max): "
        f"{min(counts)}/{statistics.median(counts):g}/{max(counts)}"
    )
    print(f"Wrote {INDEX_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
