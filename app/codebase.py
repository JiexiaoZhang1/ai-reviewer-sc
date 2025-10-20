"""Static analysis utilities for selecting code to summarize."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Iterable

from .config import Settings

MAX_TREE_DEPTH = 3

SOURCE_EXTENSIONS = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".m": "Objective-C",
    ".scala": "Scala",
    ".sql": "SQL",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".md": "Markdown",
}

SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".pdf",
    ".lock",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
}

SKIP_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "out",
    "coverage",
    ".idea",
    ".vscode",
    ".pytest_cache",
}


@dataclass
class FileCandidate:
    path: Path
    relative_path: Path
    language: str
    size_bytes: int
    weight: float


@dataclass
class SymbolInfo:
    name: str
    kind: str
    line_start: int
    line_end: int


def collect_source_candidates(root: Path, settings: Settings) -> list[FileCandidate]:
    """Return prioritized list of source files worth summarizing."""

    candidates: list[FileCandidate] = []
    for file_path in iter_source_files(root):
        size = file_path.stat().st_size
        if size == 0 or size > settings.max_file_bytes:
            continue

        ext = file_path.suffix.lower()
        language = SOURCE_EXTENSIONS.get(ext)
        if not language:
            continue

        relative = file_path.relative_to(root)
        weight = compute_weight(relative, size, language)
        candidates.append(FileCandidate(file_path, relative, language, size, weight))

    candidates.sort(key=lambda c: c.weight, reverse=True)

    if len(candidates) > settings.max_candidate_files:
        candidates = candidates[: settings.max_candidate_files]
    return candidates


def iter_source_files(root: Path) -> Iterable[Path]:
    """Yield source files under root respecting skip rules."""

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in SKIP_EXTENSIONS:
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        yield path


def compute_weight(relative_path: Path, size: int, language: str) -> float:
    """Heuristic weight balancing size, depth, and language priority."""

    depth = max(len(relative_path.parts) - 1, 0)
    depth_penalty = 1.0 / (1 + depth)
    size_score = 1.0 / (1 + size / 2000)
    language_bonus = 1.5 if language in {"Python", "TypeScript", "JavaScript"} else 1.0
    special_bonus = 1.2 if any(segment in {"src", "app", "server", "service"} for segment in relative_path.parts) else 1.0
    return depth_penalty * size_score * language_bonus * special_bonus


def build_directory_overview(root: Path) -> str:
    """Return a condensed textual tree of the repository."""

    root = root.resolve()
    lines: list[str] = []
    all_paths = sorted(root.rglob("*"), key=lambda p: (len(p.relative_to(root).parts), p.as_posix()))
    for path in all_paths:
        if path == root:
            continue
        relative = path.relative_to(root)
        depth = len(relative.parts)
        if depth > MAX_TREE_DEPTH:
            continue
        indent = "  " * (depth - 1)
        prefix = "├─ " if depth > 0 else ""
        display = f"{indent}{prefix}{relative.name}"
        if path.is_dir():
            lines.append(display + "/")
        else:
            if path.suffix.lower() in SKIP_EXTENSIONS:
                continue
            lines.append(display)
    return "\n".join(lines)


def read_text(path: Path) -> str:
    """Read file content using utf-8 with fallback."""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def extract_symbol_table(path: Path, language: str) -> list[SymbolInfo]:
    """Return lightweight symbol information for known languages."""

    text = read_text(path)
    lines = text.splitlines()
    if language in {"TypeScript", "JavaScript"}:
        symbols = _extract_typescript_symbols(lines)
    elif language == "Python":
        symbols = _extract_python_symbols(lines)
    else:
        symbols = []

    total_lines = len(lines) if lines else 1
    _fill_symbol_line_ends(symbols, total_lines)
    return symbols


CLASS_RE = re.compile(r"\bclass\s+([A-Za-z0-9_]+)")
TS_FUNCTION_RE = re.compile(r"\bfunction\s+([A-Za-z0-9_]+)\s*\(")
TS_METHOD_RE = re.compile(
    r"^\s*(public|protected|private)?\s*(static\s+)?(async\s+)?([A-Za-z0-9_]+)\s*\("
)
TS_ARROW_METHOD_RE = re.compile(
    r"^\s*(public|protected|private)?\s*(static\s+)?([A-Za-z0-9_]+)\s*=\s*(async\s+)?\("
)


def _extract_typescript_symbols(lines: list[str]) -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []
    brace_depth = 0
    class_stack: list[tuple[str, int]] = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        brace_delta = line.count("{") - line.count("}")

        class_match = CLASS_RE.search(line)
        if class_match:
            class_name = class_match.group(1)
            future_depth = brace_depth + max(brace_delta, 1)
            class_stack.append((class_name, future_depth))

        current_class = class_stack[-1][0] if class_stack else None

        method_match = TS_METHOD_RE.match(line)
        if method_match and current_class:
            method_name = method_match.group(4)
            symbols.append(
                SymbolInfo(
                    name=f"{current_class}.{method_name}",
                    kind="method",
                    line_start=idx,
                    line_end=idx,
                )
            )

        arrow_match = TS_ARROW_METHOD_RE.match(line)
        if arrow_match and current_class:
            method_name = arrow_match.group(3)
            symbols.append(
                SymbolInfo(
                    name=f"{current_class}.{method_name}",
                    kind="method",
                    line_start=idx,
                    line_end=idx,
                )
            )

        function_match = TS_FUNCTION_RE.search(line)
        if function_match:
            func_name = function_match.group(1)
            symbols.append(
                SymbolInfo(
                    name=func_name,
                    kind="function",
                    line_start=idx,
                    line_end=idx,
                )
            )

        brace_depth += brace_delta
        while class_stack and brace_depth < class_stack[-1][1]:
            class_stack.pop()

    return symbols


PY_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z0-9_]+)\s*\(")
PY_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z0-9_]+)")


def _extract_python_symbols(lines: list[str]) -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []
    class_stack: list[tuple[str, int]] = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        while class_stack and indent <= class_stack[-1][1]:
            class_stack.pop()

        class_match = PY_CLASS_RE.match(line)
        if class_match:
            class_name = class_match.group(1)
            class_stack.append((class_name, indent))
            symbols.append(
                SymbolInfo(
                    name=class_name,
                    kind="class",
                    line_start=idx,
                    line_end=idx,
                )
            )
            continue

        func_match = PY_DEF_RE.match(line)
        if func_match:
            func_name = func_match.group(1)
            if class_stack:
                func_name = f"{class_stack[-1][0]}.{func_name}"
            symbols.append(
                SymbolInfo(
                    name=func_name,
                    kind="function",
                    line_start=idx,
                    line_end=idx,
                )
            )

    return symbols


def _fill_symbol_line_ends(symbols: list[SymbolInfo], total_lines: int) -> None:
    symbols.sort(key=lambda s: s.line_start)
    for index, symbol in enumerate(symbols):
        if index + 1 < len(symbols):
            next_start = symbols[index + 1].line_start
            symbol.line_end = max(symbol.line_start, next_start - 1)
        else:
            symbol.line_end = total_lines
