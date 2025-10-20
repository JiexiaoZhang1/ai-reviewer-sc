"""High-level repository analysis pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI, OpenAIError

from .codebase import FileCandidate, build_directory_overview, collect_source_candidates
from .config import Settings
from .summarizer import FileSummary, GPTSummarizer

logger = logging.getLogger(__name__)


class ReportGenerationError(RuntimeError):
    """Raised when the LLM cannot produce a valid report."""


@dataclass
class AnalysisArtifacts:
    directory_overview: str
    candidates: List[FileCandidate]
    summaries: List[FileSummary]


def analyze_repository(problem_description: str, repo_path: Path, settings: Settings) -> Dict[str, Any]:
    """Run the full analysis pipeline and return the structured report."""

    artifacts = _gather_artifacts(problem_description, repo_path, settings)
    prompt = _compose_prompt(problem_description, artifacts, max_chars=settings.max_prompt_tokens * 4)
    raw_report = _request_report(prompt, settings)
    return _validate_report(raw_report)


def _gather_artifacts(problem_description: str, repo_path: Path, settings: Settings) -> AnalysisArtifacts:
    candidates = collect_source_candidates(repo_path, settings)
    summarizer = GPTSummarizer(settings)
    summaries = summarizer.summarize_candidates(candidates, problem_description)
    overview = build_directory_overview(repo_path)
    return AnalysisArtifacts(
        directory_overview=overview,
        candidates=candidates,
        summaries=summaries,
    )


def _compose_prompt(
    problem_description: str,
    artifacts: AnalysisArtifacts,
    *,
    max_chars: int,
) -> str:
    lines = [
        "# Task",
        "Analyze the repository and map implementation details to the requested features.",
        "",
        "## Requirements",
        problem_description.strip(),
        "",
        "## Repository Overview",
        artifacts.directory_overview or "(overview truncated)",
        "",
        "## File Summaries",
    ]

    if not artifacts.summaries:
        lines.append("No summaries available; rely on repository overview and prior knowledge.")
    else:
        for summary in artifacts.summaries:
            relative_path = summary.relative_path
            lines.extend(
                [
                    f"### {relative_path}",
                    f"Language: {summary.language}",
                    summary.summary,
                    "",
                ]
            )
            if summary.symbols:
                lines.append("Symbols with line ranges:")
                for symbol in summary.symbols:
                    if symbol.line_start == symbol.line_end:
                        line_display = str(symbol.line_start)
                    else:
                        line_display = f"{symbol.line_start}-{symbol.line_end}"
                    lines.append(f"- {symbol.name} ({symbol.kind}) lines {line_display}")
                lines.append("")

    lines.extend(
        [
            "## Output Format",
            "Return a JSON object with:",
            "- feature_analysis: array of objects with feature_description (string, Simplified Chinese) and implementation_location (array with file, function, lines).",
            "- execution_plan_suggestion: string with concise instructions to run the project in Simplified Chinese.",
            "Use the symbol table above to cite precise function or method names and provide line numbers or ranges.",
            "Do not leave function or lines as null; if only a single line is known, use that number.",
            "Only output JSON without additional commentary.",
        ]
    )
    prompt = "\n".join(lines)
    if len(prompt) > max_chars:
        prompt = prompt[: max(0, max_chars - 100)] + "\n...[context truncated due to length]..."
    return prompt


def _request_report(prompt: str, settings: Settings) -> str:
    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    system_prompt = (
        "You are an AI code analyst. "
        "Map user-facing features to the exact implementation locations in the repository. "
        "Only cite files and functions that demonstrably exist in the supplied context. "
        "All natural-language content must be written in Simplified Chinese."
    )

    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
    except OpenAIError as exc:
        logger.exception("Failed to obtain report from OpenAI: %s", exc)
        raise ReportGenerationError("Failed to generate report") from exc

    return response.output_text


def _validate_report(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReportGenerationError("Model returned invalid JSON") from exc

    if "feature_analysis" not in data or "execution_plan_suggestion" not in data:
        raise ReportGenerationError(
            "Model response missing required keys 'feature_analysis' or 'execution_plan_suggestion'."
        )

    return data
