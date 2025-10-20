"""LLM-powered code summarization utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import tiktoken
from openai import OpenAI, OpenAIError

from .codebase import (
    FileCandidate,
    SymbolInfo,
    extract_symbol_table,
    read_text,
)
from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class FileSummary:
    path: Path
    relative_path: Path
    language: str
    summary: str
    symbols: List[SymbolInfo]


@dataclass
class CodeChunk:
    text: str
    start_line: int
    end_line: int


class GPTSummarizer:
    """Summaries source files using GPT models."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.encoding = self._resolve_encoding(settings.openai_model)

    def summarize_candidates(
        self,
        candidates: Iterable[FileCandidate],
        problem_description: str,
    ) -> list[FileSummary]:
        """Generate high-level summaries for selected files."""

        summaries: list[FileSummary] = []
        for candidate in candidates:
            text = read_text(candidate.path)
            chunks = self._chunk_text(text)
            if not chunks:
                continue
            symbols = extract_symbol_table(candidate.path, candidate.language)
            chunk_summaries: list[str] = []
            for chunk in chunks:
                try:
                    chunk_summary = self._summarize_chunk(
                        chunk,
                        candidate,
                        problem_description,
                    )
                except OpenAIError as exc:
                    logger.exception("Failed to summarize %s: %s", candidate.path, exc)
                    continue
                chunk_summaries.append(chunk_summary)
            if not chunk_summaries:
                continue
            combined = self._combine_chunk_summaries(chunk_summaries)
            summaries.append(
                FileSummary(
                    path=candidate.path,
                    relative_path=candidate.relative_path,
                    language=candidate.language,
                    summary=combined,
                    symbols=symbols,
                )
            )
        return summaries

    def _summarize_chunk(
        self,
        code_chunk: CodeChunk,
        candidate: FileCandidate,
        problem_description: str,
    ) -> str:
        system_prompt = (
            "You are a senior software engineer assisting with code comprehension. "
            "Produce a concise summary highlighting interfaces, side-effects, "
            "key logic, dependencies, and potential relation to the provided requirements. "
            "Respond in Simplified Chinese."
        )

        user_prompt = (
            f"Problem description:\n{problem_description.strip()}\n\n"
            f"File: {candidate.relative_path}\n"
            f"Language: {candidate.language}\n\n"
            f"Chunk lines: {code_chunk.start_line}-{code_chunk.end_line}\n\n"
            f"Code chunk (line numbers included):\n```{candidate.language.lower()}\n{code_chunk.text}\n```"
        )

        response = self.client.responses.create(
            model=self.settings.openai_model,
            max_output_tokens=300,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.output_text.strip()

    def _combine_chunk_summaries(self, chunk_summaries: list[str]) -> str:
        """Merge chunk-level summaries into a single paragraph."""

        if len(chunk_summaries) == 1:
            return chunk_summaries[0]
        bullet_points = "\n".join(f"- {summary.strip()}" for summary in chunk_summaries)
        return f"Key points:\n{bullet_points}"

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into token-aware chunks with preserved line numbers."""

        if not text:
            return []

        lines = text.splitlines()
        max_tokens = self.settings.max_tokens_per_chunk
        chunks: list[CodeChunk] = []
        current_lines: list[str] = []
        current_tokens = 0
        chunk_start_line = 1

        for line_number, line in enumerate(lines, start=1):
            formatted = f"{line_number:04}: {line}"
            token_count = len(self.encoding.encode(formatted + "\n"))

            if current_lines and current_tokens + token_count > max_tokens:
                chunk_text = "\n".join(current_lines)
                chunk_end_line = line_number - 1
                chunks.append(
                    CodeChunk(
                        text=chunk_text,
                        start_line=chunk_start_line,
                        end_line=chunk_end_line,
                    )
                )
                current_lines = []
                current_tokens = 0
                chunk_start_line = line_number

            if not current_lines:
                chunk_start_line = line_number

            current_lines.append(formatted)
            current_tokens += token_count

        if current_lines:
            chunk_text = "\n".join(current_lines)
            chunks.append(
                CodeChunk(
                    text=chunk_text,
                    start_line=chunk_start_line,
                    end_line=len(lines),
                )
            )

        return chunks

    @staticmethod
    def _resolve_encoding(model: str):
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            return tiktoken.get_encoding("cl100k_base")
