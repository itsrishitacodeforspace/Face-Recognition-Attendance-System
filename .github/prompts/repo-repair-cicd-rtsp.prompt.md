---
name: repo-repair-cicd-rtsp
description: End-to-end repository repair with real issue validation, RTSP preview fixes, and Linux/Windows GitHub Actions hardening.
argument-hint: Optional focus or constraints for this run
agent: agent
---
You are fixing this repository end to end with production-grade discipline.

User-supplied focus/constraints: ${input}

Objectives:
1. Inspect the whole repository and find real defects only. Do not invent issues, fake findings, or meaningless tests.
2. Fix wrong logic safely with minimal behavior-breaking changes.
3. Prioritize RTSP preview reliability so preview is visible and verifiable.
4. Ensure GitHub Actions CI/CD is correctly set up for both Linux and Windows.
5. Remove unwanted files only after explicit user confirmation.

Default constraints (from user preferences):
- Unwanted files means generated caches and runtime artifacts only, unless user expands scope.
- CI must fail on any backend test or frontend build failure on both Linux and Windows.
- RTSP verification must include visible preview in frontend UI during a live stream.

Operating rules:
- Prefer root-cause fixes over band-aids.
- Keep backend/frontend API contracts aligned when changes are required.
- Maintain Windows compatibility while also supporting Linux CI.
- Use evidence for every finding: file path, line, observed behavior, and why it is wrong.
- If uncertain, run checks/tests or add targeted diagnostics before changing code.
- Do not add placeholder tests. Tests must validate real behavior and fail for real regressions.

Execution plan:
1. Repository audit
- Scan backend, frontend, and automation workflows.
- Build a prioritized defect list with severity and evidence.

2. RTSP diagnosis and repair
- Trace RTSP ingest, transport, and preview rendering path end to end.
- Fix the actual breakpoints (backend stream handling, websocket/service path, frontend preview wiring, or config mismatch).
- Validate preview visibility with concrete verification steps and outputs.

3. Logic and reliability fixes
- Address confirmed wrong logic in services/routes/components/workflows.
- Keep changes minimal, explicit, and test-backed.

4. CI/CD hardening
- Update GitHub Actions to run meaningful checks on Linux and Windows.
- Include backend tests and frontend build/test gates that reflect real runtime expectations.
- Treat backend test failures and frontend build failures as hard failures in both OS jobs.
- Avoid fake green pipelines.

5. Unwanted file cleanup (approval-gated)
- Produce a candidate list limited to generated caches/runtime artifacts, with reasons.
- Ask user approval before deleting anything.
- After approval, remove only approved files and report exactly what was removed.

Required output format:
- Section 1: Findings (real issues only)
- Section 2: Fixes applied (by file, with rationale)
- Section 3: RTSP preview verification (how it was validated)
- Section 4: CI/CD changes (Linux + Windows matrix details)
- Section 5: Cleanup proposal needing approval (if any)
- Section 6: Remaining risks and next actions

Quality bar:
- No made-up work.
- No half-complete fixes.
- If something cannot be finished in one pass, explain exactly what is blocked, what was tried, and the fastest completion path.
