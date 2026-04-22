from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic
import diskcache

from prism.constants import AI_CLI_TIMEOUT, AI_MAX_BODY_CHARS, AI_MAX_PATCH_CHARS, AI_MAX_TOKENS
from prism.models import AIAnalysis, AIConcern, PRFile, PRMetadata


class AIService:
    """Claude AI code review integration with disk-backed result cache."""

    _SYSTEM_PROMPT = """\
You are a code reviewer analyzing a pull request file diff. Return ONLY valid JSON — no markdown fences, no explanation.

Schema:
{
  "summary": "<1-2 sentence overview of what this change does>",
  "risk": "low" | "medium" | "high",
  "concerns": [
    {"title": "<short title>", "description": "<actionable description>"}
  ],
  "suggested_comment": "<optional inline comment, omit or use empty string if none>"
}

Risk levels:
- low: straightforward change, low blast radius
- medium: non-trivial logic, deserves careful review
- high: security, data integrity, or breaking change risk
"""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache = diskcache.Cache(cache_dir or Path.home() / ".cache" / "prism")

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(repo_slug: str, pr_number: int, pr_file: PRFile) -> str:
        sha = pr_file.sha or pr_file.filename
        return f"ai:{repo_slug}:{pr_number}:{sha}"

    @staticmethod
    def _build_prompt(pr: PRMetadata, pr_file: PRFile) -> str:
        patch = (pr_file.patch or "")[:AI_MAX_PATCH_CHARS]
        body_excerpt = (pr.body or "")[:AI_MAX_BODY_CHARS] or "(none)"
        return (
            f"PR title: {pr.title}\n"
            f"PR author: {pr.author}\n"
            f"PR description:\n{body_excerpt}\n\n"
            f"File: {pr_file.filename}\n"
            f"Status: {pr_file.status}\n"
            f"Additions: +{pr_file.additions}  Deletions: -{pr_file.deletions}\n\n"
            f"Diff:\n{patch}\n"
        )

    @staticmethod
    def _parse_response(raw: str) -> AIAnalysis:
        text = raw.strip()
        # Strip markdown fences if Claude wraps output in ```json ... ```
        if text.startswith("```"):
            lines = text.splitlines()
            end = -1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[1:end])
        try:
            data = json.loads(text)
            concerns = [
                AIConcern(title=c["title"], description=c["description"])
                for c in data.get("concerns", [])
            ]
            return AIAnalysis(
                summary=data.get("summary", ""),
                risk=data.get("risk", "low").lower(),
                concerns=concerns,
                suggested_comment=data.get("suggested_comment", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            return AIAnalysis(
                summary="Could not parse analysis response.",
                risk="low",
                concerns=[
                    AIConcern(
                        title="Parse error",
                        description=f"Response could not be decoded as JSON: {exc}",
                    )
                ],
            )

    @staticmethod
    def _call_claude_code(prompt: str, *, model: str, system_prompt: str) -> str:
        """Call Claude via the `claude` CLI subprocess (reuses Claude Code credentials).

        Mirrors the pattern used by https://github.com/oddur/gnosis:
        - system prompt passed via --system-prompt flag
        - content piped via stdin to avoid length limits and quoting issues
        - --no-session-persistence so reviews don't pollute conversation history
        """
        import shutil
        import subprocess

        claude_path = shutil.which("claude")
        if not claude_path:
            raise RuntimeError(
                "claude CLI not found in PATH. "
                "Set ai_backend = 'api' in ~/.config/prism/config.toml to use the Anthropic SDK instead."
            )
        result = subprocess.run(
            [
                claude_path,
                "-p",
                "--model",
                model,
                "--system-prompt",
                system_prompt,
                "--output-format",
                "json",
                "--no-session-persistence",
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=AI_CLI_TIMEOUT,
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {result.stderr.strip() or 'no error output'}")
        data = json.loads(result.stdout)
        if data.get("is_error"):
            raise RuntimeError(f"claude CLI error: {data.get('result', 'unknown error')}")
        return data["result"]

    @staticmethod
    def _get_anthropic_client() -> anthropic.Anthropic:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Create one at https://console.anthropic.com/settings/keys"
            )
        return anthropic.Anthropic(api_key=key)

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze_file(
        self,
        pr: PRMetadata,
        pr_file: PRFile,
        repo_slug: str,
        pr_number: int,
        *,
        force_refresh: bool = False,
    ) -> AIAnalysis:
        """Analyze a PR file with Claude. Synchronous — call off main thread via @work."""
        if pr_file.status == "removed":
            return AIAnalysis(
                summary="File removed — no diff to analyze.",
                risk="low",
                concerns=[],
            )

        key = self._cache_key(repo_slug, pr_number, pr_file)

        if not force_refresh and key in self._cache:
            cached = self._cache[key]
            if isinstance(cached, AIAnalysis):
                return cached

        from prism.config import load_config

        config = load_config()
        backend = config.ai_backend
        model = config.ai_model

        if backend == "claude_code":
            raw = self._call_claude_code(
                self._build_prompt(pr, pr_file),
                model=model,
                system_prompt=self._SYSTEM_PROMPT,
            )
        else:
            client = self._get_anthropic_client()
            message = client.messages.create(
                model=model,
                max_tokens=AI_MAX_TOKENS,
                system=self._SYSTEM_PROMPT,
                messages=[{"role": "user", "content": self._build_prompt(pr, pr_file)}],
            )
            raw = message.content[0].text if message.content else "{}"

        result = self._parse_response(raw)
        self._cache[key] = result
        return result
