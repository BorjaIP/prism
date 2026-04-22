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
