"""Centralised re-exports of all custom Message classes.

Import from here instead of from individual component files to decouple
consumers from the concrete widget locations. Handler names are unaffected
because Textual resolves handlers from the widget that owns the nested class.
"""

from __future__ import annotations

from prism.components.panels.ai_panel import AIPanel
from prism.components.panels.comment_list import CommentList
from prism.components.panels.file_tree import FileTreePanel
from prism.components.sections.pr_list_widget import PRListWidget

AnalysisComplete = AIPanel.AnalysisComplete
ReplyRequested = CommentList.ReplyRequested
FileSelected = FileTreePanel.FileSelected
PRSelected = PRListWidget.PRSelected
PRHighlighted = PRListWidget.PRHighlighted

__all__ = [
    "AnalysisComplete",
    "ReplyRequested",
    "FileSelected",
    "PRSelected",
    "PRHighlighted",
]
