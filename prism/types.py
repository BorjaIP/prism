from __future__ import annotations

from typing import NewType

# GitHub identifiers
RepoSlug = NewType("RepoSlug", str)
"""An 'owner/repo' GitHub repository identifier, e.g. 'torvalds/linux'."""

PRNumber = NewType("PRNumber", int)
"""A pull request number within a repository."""

CommitSHA = NewType("CommitSHA", str)
"""A full (40-char) or abbreviated git commit SHA."""

FilePath = NewType("FilePath", str)
"""A file path relative to the repository root, e.g. 'src/main.py'."""

# UI state (kept as str for JSON / API compat)
RiskLevel = str  # "low" | "medium" | "high"
ReviewEvent = str  # "APPROVE" | "REQUEST_CHANGES" | "COMMENT"
PRState = str  # "open" | "closed" | "merged"
ReviewState = str  # "APPROVED" | "CHANGES_REQUESTED" | "COMMENTED" | "DISMISSED"
