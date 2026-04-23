# Contributing to Face Recognition Attendance System

Thank you for considering contributing! This document explains how to get involved, submit changes, and keep the codebase consistent.

---

## Table of Contents

- [Getting Started](#getting-started)
- [How to Submit a Pull Request](#how-to-submit-a-pull-request)
- [Branch Naming Conventions](#branch-naming-conventions)
- [Code Style Guidelines](#code-style-guidelines)
- [Docstring Format](#docstring-format)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Commit Message Format](#commit-message-format)

---

## Getting Started

### 1. Fork the repository

Click **Fork** at the top-right of the repository page. This creates your own copy.

### 2. Clone your fork

```bash
git clone https://github.com/<your-username>/face-recognition-attendance.git
cd face-recognition-attendance
```

### 3. Add the upstream remote

```bash
git remote add upstream https://github.com/<original-owner>/face-recognition-attendance.git
```

### 4. Set up the development environment

Follow the [Installation](README.md#-installation) steps in the README.

### 5. Keep your fork up to date

Before starting any new work:

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

---

## How to Submit a Pull Request

1. **Create a branch** from `main` following the [naming conventions](#branch-naming-conventions) below.

2. **Make your changes.** Keep each PR focused on a single concern (bug fix, feature, refactor). Do not mix unrelated changes.

3. **Run the test suite** and make sure everything passes:

   ```bash
   cd backend
   source .venv/bin/activate
   pytest -q
   ```

4. **Lint your code:**

   ```bash
   # Install linting tools if not already present
   pip install ruff black

   ruff check backend/
   black --check backend/
   ```

5. **Push your branch:**

   ```bash
   git push origin feat/your-feature-name
   ```

6. **Open a Pull Request** against the `main` branch of the upstream repository.

7. **Fill in the PR template** — describe *what* changed and *why*. Link any related issues with `Closes #<issue-number>`.

8. A maintainer will review your PR. Be responsive to review comments — address them and push fixes to the same branch.

---

## Branch Naming Conventions

Use kebab-case with a descriptive prefix:

| Prefix | When to use | Example |
|---|---|---|
| `feat/` | New features | `feat/rtsp-stream-support` |
| `fix/` | Bug fixes | `fix/cooldown-race-condition` |
| `docs/` | Documentation only | `docs/update-api-reference` |
| `refactor/` | Code restructuring (no behaviour change) | `refactor/face-service-cleanup` |
| `test/` | Adding or fixing tests | `test/attendance-cooldown-edge-cases` |
| `chore/` | Build system, deps, CI changes | `chore/bump-insightface-0.7.4` |
| `hotfix/` | Critical production fixes | `hotfix/auth-token-expiry-bug` |

---

## Code Style Guidelines

All Python code must follow **PEP 8** with the following tooling enforced:

### Formatter — Black

```bash
black backend/
```

- Line length: **88 characters** (Black default)
- Do not manually configure line breaks within expressions — let Black handle it

### Linter — Ruff

```bash
ruff check backend/ --fix
```

Common rules enforced:
- `F` — Pyflakes (unused imports, undefined names)
- `E`, `W` — PEP 8 errors and warnings
- `I` — isort-compatible import ordering

### Import ordering

```python
# 1. Standard library
import os
import json
from pathlib import Path

# 2. Third-party
import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local application
from app.config import settings
from app.services.face_recognition import FaceRecognitionService
```

### Type hints

All function signatures **must** include type hints:

```python
# ✅ Good
async def get_person(person_id: int, db: AsyncSession) -> PersonSchema:
    ...

# ❌ Bad
async def get_person(person_id, db):
    ...
```

### No magic numbers

```python
# ✅ Good
EMBEDDING_DIM = 512
query_vector = np.zeros(EMBEDDING_DIM)

# ❌ Bad
query_vector = np.zeros(512)
```

---

## Docstring Format

Use **Google-style docstrings** for all public functions, classes, and modules.

### Function example

```python
def compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two L2-normalised embedding vectors.

    Args:
        vec_a: First embedding vector of shape (512,).
        vec_b: Second embedding vector of shape (512,).

    Returns:
        Cosine similarity score in the range [-1.0, 1.0].

    Raises:
        ValueError: If either vector has zero norm.

    Example:
        >>> a = np.array([1.0, 0.0])
        >>> b = np.array([0.0, 1.0])
        >>> compute_cosine_similarity(a, b)
        0.0
    """
```

### Class example

```python
class FaceRecognitionService:
    """Manages face embedding extraction and FAISS index operations.

    Wraps InsightFace's buffalo_l model for detection and embedding,
    and maintains a FAISS IndexFlatIP for fast nearest-neighbour lookup.

    Attributes:
        model: The loaded InsightFace FaceAnalysis model.
        index: FAISS index holding all enrolled identity vectors.
        labels: List of person names corresponding to index rows.
    """
```

---

## Reporting Bugs

Please use the GitHub Issues tab and include the following information:

---

**Bug Report Template:**

```
### Description
A clear and concise description of the bug.

### Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

### Expected Behaviour
What you expected to happen.

### Actual Behaviour
What actually happened. Include error messages and stack traces.

### Environment
- OS: [e.g. Ubuntu 22.04 / Windows 11]
- Python version: [e.g. 3.11.9]
- Node version: [e.g. 20.12.0]
- GPU / CUDA: [e.g. NVIDIA RTX 3080 / CUDA 12.1 / CPU only]
- Browser (if frontend issue): [e.g. Chrome 124]

### Additional Context
Any other context, screenshots, or log output that might help.
```

---

## Suggesting Features

Open a GitHub Issue with the label `enhancement`. Include:

1. **Use case** — What problem does this feature solve? Who benefits?
2. **Proposed solution** — How would the feature work at a high level?
3. **Alternatives considered** — What other approaches did you think about?
4. **Acceptance criteria** — How will we know when this feature is done?

---

## Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <short summary>

[optional body — explain WHY, not WHAT]

[optional footer — Closes #123, Breaking: ...]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

**Examples:**

```
feat(recognition): add RTSP stream support via GStreamer pipeline

fix(auth): refresh token now correctly invalidated on logout

Closes #47

docs(readme): add CUDA setup notes for RTX 40-series

test(attendance): add edge case for exactly 0-second cooldown
```

**Rules:**
- Use the **imperative mood** in the subject: "add feature" not "added feature"
- Keep the subject line under **72 characters**
- Do not end the subject line with a period
- Reference issues in the footer, not the subject line

---

## Questions?

Open a [GitHub Discussion](../../discussions) or file an issue with the label `question`.

We appreciate every contribution, no matter how small. Thank you! 🙏
