# CE Brief

Run: example-run
Spec: spec-example
Status: ready
Return route: driftlock-fixer

## Trigger

Reviewer rejected the implementation and the failure needs synthesis before another retry.

## Failure Clusters

- review_reject: Reviewer rejected the implementation and the failure needs synthesis before another retry. (high)

## Root-Cause Hypothesis

The current failure loop is likely caused by an untested assumption in the previous fix strategy, not by a lack of another retry.

## What Did Not Work

- Prior implementation reached reviewer but did not satisfy review criteria.

## Next Fix Strategy

- Pick one failure cluster and write the smallest falsifiable fix hypothesis.
- Change only the code or spec surface needed for that hypothesis.
- Run the build, regression smoke, and review evidence that previously failed.
- Return through implementer/fixer, then builder, then reviewer before QA or handoff.

## Verification Plan

- Rerun the failed build or smoke command.
- Refresh review-report.json with reviewer_read_only=true and code_edits_made=false.
- Refresh quality-report.json before handoff.

## Intent Impact

Amendment required: false
Reason: Failure can be handled inside the locked implementation intent.

## Learning Note

Status: not-needed
Key: review_reject
Prevention: Before retrying, state the root-cause hypothesis, the evidence that supports it, and the verification command that will disprove it.
