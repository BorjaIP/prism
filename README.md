# PRism

Terminal UI for reviewing GitHub pull requests. Three-panel layout: file tree, diff viewer, AI analysis.

## Usage

```bash
export GITHUB_TOKEN=<your-token>
prism review owner/repo 142
```

## Prerequisites

- Python 3.11+
- `delta` (optional, for syntax-highlighted diffs): `brew install git-delta`
