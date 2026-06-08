# Execution Contract

## Agent Roles

- Task splitter creates tasks, dependencies, branches, and task-level acceptance criteria.
- Implementer/fixer changes code.
- Builder runs build, lint, tests, and runtime checks.
- Reviewer evaluates correctness, maintainability, scope control, and evidence.
- Gatekeeper decides pass, debug, CE, amend, or blocked.

## Loop

1. Validate Locked Spec.
2. Create Task Graph.
3. Validate task coverage against success criteria and acceptance scenarios.
4. Implement task on its branch.
5. Build/test.
6. Review.
7. Gate.
8. Merge or route failure.
9. Run integration gate.
10. Produce final handoff.

## Gate Routing

- Build/test fail: route to Debug Mode, then implementer/fixer.
- Review reject: route to implementer/fixer if the fix is local and obvious.
- Repeated review reject or structural issue: route to CE, then implementer/fixer.
- Spec ambiguity, contradiction, or product change: route to `driftlock-amend`.
- All task gates pass and integration evidence passes: final handoff.

## Task Split Gate

- Every success criterion is covered by at least one task.
- Every acceptance scenario is covered by at least one task.
- Dependencies reference existing tasks.
- Each task has acceptance criteria and a branch name.

## Final Handoff Gate

- All tasks have passing build/test evidence.
- All reviews are approved or resolved.
- Integration gate passes.
- No open amendment request remains.
