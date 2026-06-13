"""Report builders: browser evidence, quality report, debrief, spec-gate report."""
from __future__ import annotations

import argparse
import re
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from .validators import *  # noqa: F401,F403


def finding(
    findings: list[dict[str, Any]],
    category: str,
    severity: str,
    summary: str,
    recommendation: str,
    source: str,
) -> None:
    findings.append(
        {
            "id": f"SG-{len(findings) + 1:03d}",
            "category": category,
            "severity": severity,
            "summary": summary,
            "recommendation": recommendation,
            "source": source,
        }
    )


def explicit_evidence(spec: dict[str, Any], key: str) -> Any:
    evidence = spec.get("spec_evidence")
    if isinstance(evidence, dict):
        return evidence.get(key)
    return None


def evidence_has_content(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value) and any(evidence_has_content(item) for item in value)
    if isinstance(value, dict):
        status = value.get("status")
        reason = value.get("reason")
        if status == "not_applicable" and non_empty_string(reason):
            return True
        return any(evidence_has_content(item) for item in value.values())
    return value is not None


def evidence_status(value: Any) -> str:
    if isinstance(value, dict) and value.get("status") == "not_applicable" and non_empty_string(value.get("reason")):
        return "not_applicable"
    if evidence_has_content(value):
        return "pass"
    return "fail"


def category_summary(status: str, pass_summary: str, fail_summary: str, na_summary: str | None = None) -> str:
    if status == "pass":
        return pass_summary
    if status == "not_applicable":
        return na_summary or pass_summary
    return fail_summary


def accepted_decision_count(decision_log: list[dict[str, Any]] | None) -> int:
    if not decision_log:
        return 0
    return sum(1 for item in decision_log if isinstance(item, dict) and item.get("status") == "accepted")


def read_decision_log(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LodestarError(f"Decision log not found: {path}") from exc
    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise LodestarError(f"Invalid JSONL in {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise LodestarError(f"Invalid decision log entry in {path}:{line_number}: expected object")
        entries.append(value)
    return entries


def read_optional_text(path: Path | None, label: str) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LodestarError(f"{label} not found: {path}") from exc


def read_optional_json(path: Path | None, label: str) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise LodestarError(f"{label} not found: {path}")
    return read_json(path)


def browser_finding(
    findings: list[dict[str, Any]],
    check: str,
    severity: str,
    summary: str,
    recommendation: str,
    source: str,
) -> None:
    findings.append(
        {
            "id": f"BR-{len(findings) + 1:03d}",
            "check": check,
            "severity": severity,
            "summary": summary,
            "recommendation": recommendation,
            "source": source,
        }
    )


def browser_check(status: str, summary: str, evidence: list[str] | None = None) -> dict[str, Any]:
    return {"status": status, "summary": summary, "evidence": evidence or []}


def parse_html_page(html_text: str) -> dict[str, Any]:
    parser = BrowserEvidenceHTMLParser()
    parser.feed(html_text)
    parser.close()
    return parser.page()


def count_snapshot_value(value: Any) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, list):
        return len(value)
    return 0


def rendered_snapshot_console_errors(snapshot: dict[str, Any]) -> list[str]:
    raw_errors = snapshot.get("console_errors")
    if raw_errors is None:
        raw_errors = snapshot.get("errors")
    if raw_errors is None and isinstance(snapshot.get("console"), dict):
        raw_errors = snapshot["console"].get("errors")
    if isinstance(raw_errors, list):
        return [str(item) for item in raw_errors if str(item).strip()]
    if isinstance(raw_errors, str) and raw_errors.strip():
        return [raw_errors.strip()]
    return []


def rendered_snapshot_screenshot(snapshot: dict[str, Any]) -> str:
    for key in ("screenshot", "screenshot_path"):
        if non_empty_string(snapshot.get(key)):
            return str(snapshot[key])
    artifacts = snapshot.get("artifacts")
    if isinstance(artifacts, dict) and non_empty_string(artifacts.get("screenshot")):
        return str(artifacts["screenshot"])
    return ""


def page_from_rendered_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    raw_page = snapshot.get("page") if isinstance(snapshot.get("page"), dict) else snapshot
    title = str(raw_page.get("title", ""))
    text = str(raw_page.get("text") or raw_page.get("body_text") or raw_page.get("bodyText") or raw_page.get("visible_text") or "")
    raw_headings = raw_page.get("headings")
    headings = [str(item) for item in raw_headings if str(item).strip()] if isinstance(raw_headings, list) else []
    html_lang_raw = raw_page.get("html_lang")
    lang_raw = raw_page.get("lang")
    return {
        "title": title,
        "text_sample": text[:500],
        "_text_search": text,
        "text_length": len(text),
        "headings": headings[:12],
        "links": count_snapshot_value(raw_page.get("links")),
        "buttons": count_snapshot_value(raw_page.get("buttons")),
        "buttons_without_name": count_snapshot_value(raw_page.get("buttons_without_name")),
        "inputs": count_snapshot_value(raw_page.get("inputs")),
        "inputs_without_label": count_snapshot_value(raw_page.get("inputs_without_label")),
        "images": count_snapshot_value(raw_page.get("images")),
        "images_without_alt": count_snapshot_value(raw_page.get("images_without_alt")),
        "aria_labels": count_snapshot_value(raw_page.get("aria_labels")),
        "html_lang": bool(html_lang_raw) or non_empty_string(lang_raw),
    }


def fetch_url_text(url: str, timeout_seconds: int) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": "LodestarBrowserEvidence/0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content_type = response.headers.get("content-type", "")
            charset_match = re.search(r"charset=([^;]+)", content_type, re.IGNORECASE)
            charset = charset_match.group(1).strip() if charset_match else "utf-8"
            body = response.read().decode(charset, errors="replace")
            return body, f"HTTP {getattr(response, 'status', 200)} {content_type}".strip()
    except HTTPError as exc:
        raise LodestarError(f"Browser target returned HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise LodestarError(f"Browser target could not be reached: {url}: {exc.reason}") from exc


def screenshot_artifact_status(path_text: str | None) -> tuple[str, list[str]]:
    if not path_text:
        return "not_applicable", []
    path = Path(path_text)
    if path.exists() and path.is_file() and path.stat().st_size > 0:
        return "pass", [str(path)]
    return "fail", [str(path)]


def console_errors_from_path(path_text: str | None) -> list[str]:
    if not path_text:
        return []
    path = Path(path_text)
    if not path.exists():
        raise LodestarError(f"Console errors file not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return [line.strip() for line in text.splitlines() if line.strip()]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, dict):
        raw_errors = value.get("errors") or value.get("console_errors") or []
        if isinstance(raw_errors, list):
            return [str(item) for item in raw_errors if str(item).strip()]
    return [text]


def build_browser_evidence(
    run_id: str,
    mode: str,
    source: str,
    html_text: str,
    expected_text: list[str] | None = None,
    viewport_name: str = "desktop",
    screenshot_path: str | None = None,
    console_errors_path: str | None = None,
    console_errors: list[str] | None = None,
    snapshot_page: dict[str, Any] | None = None,
    load_summary: str | None = None,
) -> dict[str, Any]:
    expected_text = expected_text or []
    viewport = dict(BROWSER_VIEWPORTS.get(viewport_name, BROWSER_VIEWPORTS["desktop"]))
    viewport["name"] = viewport_name if viewport_name in BROWSER_VIEWPORTS else "desktop"
    page = snapshot_page if isinstance(snapshot_page, dict) else parse_html_page(html_text)
    page_search_text = str(page.pop("_text_search", page.get("text_sample", "")))
    findings: list[dict[str, Any]] = []
    checks: dict[str, dict[str, Any]] = {}

    load_status = "pass" if html_text.strip() or page_search_text.strip() or non_empty_string(page.get("title")) else "fail"
    if load_status == "fail":
        browser_finding(findings, "load", "critical", "Browser target produced no HTML.", "Start the app or provide a reachable page before QA.", source)
    checks["load"] = browser_check(load_status, load_summary or ("Loaded target HTML." if load_status == "pass" else "Target did not load."), [source])

    title_status = "pass" if non_empty_string(page.get("title")) else "warning"
    if title_status == "warning":
        browser_finding(findings, "title", "medium", "Page title is empty.", "Add a meaningful title for browser QA and user orientation.", "page.title")
    checks["title"] = browser_check(title_status, "Page title is present." if title_status == "pass" else "Page title is missing.", [str(page.get("title", ""))])

    page_text = " ".join([str(page.get("title", "")), page_search_text]).lower()
    missing_expected = [item for item in expected_text if item.lower() not in page_text]
    if not expected_text:
        expected_status = "not_applicable"
        expected_summary = "No expected text assertions were requested."
    elif missing_expected:
        expected_status = "fail"
        expected_summary = "Expected text was not found in the page."
        browser_finding(
            findings,
            "expected_text",
            "high",
            f"Expected text missing: {', '.join(missing_expected)}.",
            "Verify the app rendered the approved surface or update the expected text.",
            "expected-text",
        )
    else:
        expected_status = "pass"
        expected_summary = "Expected text assertions passed."
    checks["expected_text"] = browser_check(expected_status, expected_summary, expected_text)

    collected_console_errors = list(console_errors or [])
    collected_console_errors.extend(console_errors_from_path(console_errors_path))
    if collected_console_errors:
        console_status = "fail"
        browser_finding(
            findings,
            "console",
            "high",
            f"Browser console errors were recorded: {len(collected_console_errors)}.",
            "Fix console errors or document why they are benign before handoff.",
            console_errors_path or "console",
        )
    elif console_errors_path:
        console_status = "pass"
    else:
        console_status = "not_applicable"
    checks["console"] = browser_check(
        console_status,
        "No console errors were recorded." if console_status == "pass" else ("Console error evidence was not provided." if console_status == "not_applicable" else "Console errors were recorded."),
        collected_console_errors[:5],
    )

    accessibility_issues = []
    if not page.get("html_lang"):
        accessibility_issues.append("html lang missing")
    if page.get("images_without_alt", 0):
        accessibility_issues.append(f"images_without_alt={page.get('images_without_alt')}")
    if page.get("inputs_without_label", 0):
        accessibility_issues.append(f"inputs_without_label={page.get('inputs_without_label')}")
    if page.get("buttons_without_name", 0):
        accessibility_issues.append(f"buttons_without_name={page.get('buttons_without_name')}")
    if accessibility_issues:
        accessibility_status = "warning"
        browser_finding(
            findings,
            "accessibility_baseline",
            "medium",
            f"Accessibility baseline has warnings: {', '.join(accessibility_issues)}.",
            "Add labels, alt text, button names, or html lang before production handoff.",
            "browser-accessibility-baseline",
        )
    else:
        accessibility_status = "pass"
    checks["accessibility_baseline"] = browser_check(
        accessibility_status,
        "Accessibility baseline passed." if accessibility_status == "pass" else "Accessibility baseline has warnings.",
        accessibility_issues,
    )

    responsive_status = "pass" if viewport["width"] >= 320 and viewport["height"] >= 568 else "warning"
    if responsive_status == "warning":
        browser_finding(findings, "responsive_baseline", "medium", "Viewport is below the supported smoke baseline.", "Run browser QA on mobile or desktop baseline viewport.", "viewport")
    checks["responsive_baseline"] = browser_check(responsive_status, "Viewport baseline is usable." if responsive_status == "pass" else "Viewport baseline is too small.", [f"{viewport['name']}={viewport['width']}x{viewport['height']}"])

    screenshot_status, screenshot_evidence = screenshot_artifact_status(screenshot_path)
    if screenshot_status == "fail":
        browser_finding(findings, "screenshot", "high", "Screenshot artifact path was provided but does not exist.", "Capture or attach the screenshot artifact before handoff.", screenshot_path or "screenshot")
    checks["screenshot"] = browser_check(
        screenshot_status,
        "Screenshot artifact exists." if screenshot_status == "pass" else ("Screenshot evidence was not requested." if screenshot_status == "not_applicable" else "Screenshot artifact is missing."),
        screenshot_evidence,
    )

    critical_findings = sum(1 for item in findings if item["severity"] == "critical")
    high_findings = sum(1 for item in findings if item["severity"] == "high")
    medium_findings = sum(1 for item in findings if item["severity"] == "medium")
    low_findings = sum(1 for item in findings if item["severity"] == "low")
    status = "fail" if critical_findings or high_findings else "pass"

    return {
        "run_id": run_id,
        "status": status,
        "mode": mode,
        "target": {
            "type": mode if mode in {"url", "html", "snapshot", "manual"} else "html",
            "source": source,
        },
        "captured_at": utc_now(),
        "upstream_source": {
            "repo": "gstack",
            "adapter": "lodestar-browser-qa",
            "paths": [
                "third_party/upstream/gstack/qa",
                "third_party/upstream/gstack/qa-only",
                "third_party/upstream/gstack/design-review",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-test-browser",
            ],
        },
        "viewport": viewport,
        "page": page,
        "checks": checks,
        "findings": findings,
        "metrics": {
            "total_findings": len(findings),
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "medium_findings": medium_findings,
            "low_findings": low_findings,
            "check_pass_count": sum(1 for item in checks.values() if item["status"] == "pass"),
            "check_fail_count": sum(1 for item in checks.values() if item["status"] == "fail"),
            "check_warning_count": sum(1 for item in checks.values() if item["status"] == "warning"),
            "check_not_applicable_count": sum(1 for item in checks.values() if item["status"] == "not_applicable"),
        },
        "artifacts": {
            "screenshot": screenshot_path or "",
            "console_errors": console_errors_path or "",
        },
    }


def build_responsive_matrix(
    run_id: str,
    evidence_by_viewport: dict[str, dict[str, Any]],
    require_screenshots: bool = False,
) -> dict[str, Any]:
    viewports: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, str]] = []

    for name in RESPONSIVE_MATRIX_VIEWPORTS:
        evidence = evidence_by_viewport.get(name, {})
        viewport = evidence.get("viewport") if isinstance(evidence.get("viewport"), dict) else {}
        artifacts = evidence.get("artifacts") if isinstance(evidence.get("artifacts"), dict) else {}
        screenshot = str(artifacts.get("screenshot") or "")
        evidence_findings = evidence.get("findings") if isinstance(evidence.get("findings"), list) else []
        browser_status = evidence.get("status")
        actual_name = str(viewport.get("name") or "")

        viewport_findings: list[str] = []
        if browser_status != "pass":
            viewport_findings.append("browser evidence did not pass")
        if actual_name != name:
            viewport_findings.append(f"browser evidence viewport is {actual_name or 'missing'}, expected {name}")
        if require_screenshots and not screenshot:
            viewport_findings.append("screenshot artifact is required")
        for item in evidence_findings:
            if isinstance(item, dict) and item.get("summary"):
                viewport_findings.append(str(item["summary"]))

        status = "fail" if viewport_findings else "pass"
        viewports[name] = {
            "status": status,
            "width": int(viewport.get("width") or BROWSER_VIEWPORTS[name]["width"]),
            "height": int(viewport.get("height") or BROWSER_VIEWPORTS[name]["height"]),
            "browser_evidence": str(evidence.get("_path") or ""),
            "screenshot": screenshot,
            "findings": viewport_findings,
        }
        findings.extend({"viewport": name, "summary": item} for item in viewport_findings)

    pass_count = sum(1 for item in viewports.values() if item["status"] == "pass")
    fail_count = len(RESPONSIVE_MATRIX_VIEWPORTS) - pass_count
    return {
        "run_id": run_id,
        "status": "fail" if findings else "pass",
        "required_viewports": list(RESPONSIVE_MATRIX_VIEWPORTS),
        "viewports": viewports,
        "findings": findings,
        "metrics": {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "finding_count": len(findings),
        },
    }


def quality_finding(
    findings: list[dict[str, Any]],
    check: str,
    severity: str,
    summary: str,
    recommendation: str,
    source: str,
    owner: str = "fixer",
) -> None:
    findings.append(
        {
            "id": f"QA-{len(findings) + 1:03d}",
            "check": check,
            "severity": severity,
            "summary": summary,
            "recommendation": recommendation,
            "source": source,
            "owner": owner,
        }
    )


def quality_check(status: str, summary: str, evidence: list[str] | None = None) -> dict[str, Any]:
    return {"status": status, "summary": summary, "evidence": evidence or []}


def command_statuses_pass(commands: Any) -> bool:
    if not isinstance(commands, list) or not commands:
        return False
    for command in commands:
        if not isinstance(command, dict):
            return False
        if command.get("status") != "pass":
            return False
    return True


def command_names(commands: Any) -> list[str]:
    if not isinstance(commands, list):
        return []
    names = []
    for command in commands:
        if isinstance(command, dict) and non_empty_string(command.get("cmd")):
            names.append(str(command["cmd"]))
    return names


def task_cover_ids_from_execution_plan(execution_plan: dict[str, Any]) -> set[str]:
    covered: set[str] = set()
    tasks = execution_plan.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict) and isinstance(task.get("covers"), list):
                covered.update(item for item in task["covers"] if isinstance(item, str))
    return covered


def integration_evidence_status(spec: dict[str, Any], proof_bundle: dict[str, Any] | None = None) -> str:
    if proof_bundle:
        gates = proof_bundle.get("gates")
        if isinstance(gates, dict) and gates.get("integration") == "pass":
            return "pass"
    return evidence_status(explicit_evidence(spec, "integrations"))


def build_quality_report(
    run_id: str,
    spec: dict[str, Any],
    execution_plan: dict[str, Any],
    build_evidence: dict[str, Any],
    review_report: dict[str, Any],
    ux_lock_text: str = "",
    proof_bundle: dict[str, Any] | None = None,
    browser_evidence: dict[str, Any] | None = None,
    artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    checks: dict[str, dict[str, Any]] = {}
    spec_id = spec.get("id") if non_empty_string(spec.get("id")) else execution_plan.get("spec_id", "unknown-spec")
    proof_bundle = proof_bundle or {}
    browser_evidence = browser_evidence or {}
    browser_passed = bool(browser_evidence) and browser_evidence.get("status") == "pass"
    browser_target = ""
    if isinstance(browser_evidence.get("target"), dict):
        browser_target = str(browser_evidence["target"].get("source", ""))

    execution_status = "pass"
    execution_evidence: list[str] = []
    metrics = execution_plan.get("metrics")
    tasks = execution_plan.get("tasks")
    if execution_plan.get("status") != "done":
        execution_status = "fail"
        quality_finding(
            findings,
            "execution_completion",
            "critical",
            "Execution plan is not complete.",
            "Finish all task execution loops before QA and handoff.",
            "execution-plan.status",
        )
    if isinstance(metrics, dict):
        execution_evidence.append(f"done={metrics.get('done')} total={metrics.get('total')} blocked={metrics.get('blocked')}")
        if metrics.get("total") != metrics.get("done"):
            execution_status = "fail"
            quality_finding(
                findings,
                "execution_completion",
                "critical",
                "Not all execution tasks are done.",
                "Return unfinished tasks through implementer, builder, reviewer, fixer, or debrief as required.",
                "execution-plan.metrics",
            )
        if metrics.get("blocked", 0):
            execution_status = "fail"
            quality_finding(
                findings,
                "execution_completion",
                "high",
                "Execution plan still contains blocked tasks.",
                "Resolve blocked tasks or request an amendment before QA can pass.",
                "execution-plan.metrics.blocked",
            )
    else:
        execution_status = "fail"
        quality_finding(findings, "execution_completion", "critical", "Execution metrics are missing.", "Refresh execution-status before QA.", "execution-plan.metrics")
    if isinstance(tasks, list):
        not_done = [task.get("task_id", "unknown") for task in tasks if isinstance(task, dict) and task.get("state") != "TASK_DONE"]
        if not_done:
            execution_status = "fail"
            quality_finding(
                findings,
                "execution_completion",
                "critical",
                f"Tasks are not done: {', '.join(str(item) for item in not_done)}.",
                "Complete every task state before QA.",
                "execution-plan.tasks",
            )
    checks["execution_completion"] = quality_check(execution_status, "All task states are complete." if execution_status == "pass" else "Execution loop is incomplete.", execution_evidence)

    build_status = "pass" if build_evidence.get("status") == "pass" and command_statuses_pass(build_evidence.get("commands")) else "fail"
    if build_status == "fail":
        quality_finding(
            findings,
            "build_verification",
            "critical",
            "Build evidence did not pass.",
            "Route to fixer and rerun builder verification.",
            "build-evidence",
        )
    checks["build_verification"] = quality_check(
        build_status,
        "Build and command evidence passed." if build_status == "pass" else "Build evidence is failing or incomplete.",
        command_names(build_evidence.get("commands")),
    )

    review_status = "pass"
    if review_report.get("status") != "approved":
        review_status = "fail"
        quality_finding(findings, "review_integrity", "critical", "Review report is not approved.", "Route rejected findings to fixer or debrief.", "review-report.status")
    if review_report.get("reviewer_read_only") is not True or review_report.get("code_edits_made") is not False:
        review_status = "fail"
        quality_finding(
            findings,
            "review_integrity",
            "critical",
            "Reviewer integrity contract was violated.",
            "Discard reviewer code edits and rerun review as read-only.",
            "review-report.reviewer_read_only",
            "debrief",
        )
    critical_review_findings = []
    for item in review_report.get("findings", []):
        if isinstance(item, dict) and item.get("severity") in {"P0", "P1"} and item.get("requires_verification") is True:
            critical_review_findings.append(item.get("summary", "unresolved finding"))
    if critical_review_findings:
        review_status = "fail"
        quality_finding(
            findings,
            "review_integrity",
            "high",
            f"Review has unresolved high-priority findings: {len(critical_review_findings)}.",
            "Resolve high-priority review findings before QA passes.",
            "review-report.findings",
        )
    checks["review_integrity"] = quality_check(review_status, "Review integrity passed." if review_status == "pass" else "Review integrity failed.", critical_review_findings)

    product_shape = spec.get("product_shape")
    ux_status = "pass"
    ux_evidence = []
    if isinstance(product_shape, dict):
        ux_evidence.append(f"approved_preview={product_shape.get('approved_preview')}")
    if browser_evidence:
        page = browser_evidence.get("page")
        if isinstance(page, dict):
            ux_evidence.append(f"browser_title={page.get('title', '')}")
        if browser_target:
            ux_evidence.append(f"browser_target={browser_target}")
        if browser_evidence.get("status") == "fail":
            ux_status = "fail"
            quality_finding(
                findings,
                "ux_alignment",
                "high",
                "Browser QA evidence failed for the delivered surface.",
                "Return to fixer or UX guard and refresh browser-evidence.json.",
                "browser-evidence.status",
            )
    if not isinstance(product_shape, dict) or product_shape.get("approved_preview") is not True:
        ux_status = "fail"
        quality_finding(
            findings,
            "ux_alignment",
            "critical",
            "Approved UX preview evidence is missing.",
            "Return to UX approval or request an amendment before QA passes.",
            "locked-spec.product_shape.approved_preview",
            "amend-advisor",
        )
    if ux_lock_text.strip():
        ux_evidence.append("shape-lock.md present")
        if "Approved" not in ux_lock_text and "approved" not in ux_lock_text:
            ux_status = "fail"
            quality_finding(
                findings,
                "ux_alignment",
                "high",
                "UX lock does not contain approval evidence.",
                "Regenerate shape-lock.md from the approved UX preview.",
                "shape-lock.md",
                "amend-advisor",
            )
    else:
        ux_status = "fail"
        quality_finding(
            findings,
            "ux_alignment",
            "high",
            "UX lock artifact is missing.",
            "Run UX guard with the approved UX lock before QA.",
            "shape-lock.md",
            "amend-advisor",
        )
    checks["ux_alignment"] = quality_check(ux_status, "UX approval and lock evidence are present." if ux_status == "pass" else "UX alignment evidence is incomplete.", ux_evidence)

    required_covers = spec_cover_ids(spec)
    actual_covers = task_cover_ids_from_execution_plan(execution_plan)
    missing_covers = sorted(required_covers - actual_covers)
    coverage_status = "pass" if required_covers and not missing_covers else "fail"
    if not required_covers:
        quality_finding(
            findings,
            "acceptance_coverage",
            "high",
            "Spec has no acceptance coverage IDs.",
            "Return to spec gate and add testable success criteria or scenarios.",
            "locked-spec.success_criteria",
            "amend-advisor",
        )
    if missing_covers:
        quality_finding(
            findings,
            "acceptance_coverage",
            "high",
            f"Execution plan does not cover: {', '.join(missing_covers)}.",
            "Split or add tasks until every success criterion and acceptance scenario is covered.",
            "execution-plan.tasks.covers",
        )
    checks["acceptance_coverage"] = quality_check(
        coverage_status,
        "Execution tasks cover all success criteria and scenarios." if coverage_status == "pass" else "Acceptance coverage is incomplete.",
        sorted(actual_covers),
    )

    commands = command_names(build_evidence.get("commands"))
    smoke_terms = ("test", "lint", "build", "typecheck", "e2e", "playwright", "vitest", "pytest")
    command_smoke = any(any(term in command.lower() for term in smoke_terms) for command in commands)
    has_smoke = command_smoke or browser_passed
    regression_status = "pass" if build_status == "pass" and has_smoke and browser_passed else "fail"
    if not has_smoke:
        quality_finding(
            findings,
            "regression_smoke",
            "high",
            "No recognizable regression smoke command was recorded.",
            "Run at least one test, lint, build, typecheck, or browser smoke command before QA passes.",
            "build-evidence.commands",
        )
    if not browser_evidence:
        quality_finding(
            findings,
            "regression_smoke",
            "high",
            "Browser QA evidence is missing.",
            "Run browser-collect against the delivered surface before final QA.",
            "browser-evidence.json",
        )
    elif browser_evidence.get("status") == "fail":
        quality_finding(
            findings,
            "regression_smoke",
            "high",
            "Browser QA evidence failed.",
            "Fix the delivered surface and refresh browser-evidence.json.",
            "browser-evidence.status",
        )
    checks["regression_smoke"] = quality_check(
        regression_status,
        "Regression smoke command evidence is present." if regression_status == "pass" else "Regression smoke evidence is missing.",
        commands + ([f"browser-evidence={browser_target or 'present'}"] if browser_passed else []),
    )

    integration_status = integration_evidence_status(spec, proof_bundle)
    if integration_status == "fail":
        quality_finding(
            findings,
            "integration_readiness",
            "high",
            "Integration evidence is missing.",
            "Add integration checks or explicitly mark integrations not applicable with a reason.",
            "locked-spec.spec_evidence.integrations",
            "amend-advisor",
        )
    checks["integration_readiness"] = quality_check(
        integration_status,
        "Integration evidence is present." if integration_status == "pass" else ("Integrations are explicitly not applicable." if integration_status == "not_applicable" else "Integration evidence is missing."),
        [str(explicit_evidence(spec, "integrations"))],
    )

    accessibility_evidence = explicit_evidence(spec, "accessibility")
    browser_accessibility = None
    if isinstance(browser_evidence.get("checks"), dict):
        browser_accessibility = browser_evidence["checks"].get("accessibility_baseline")
    if isinstance(browser_accessibility, dict) and browser_accessibility.get("status") in {"pass", "warning", "fail"}:
        accessibility_status = str(browser_accessibility["status"])
        accessibility_sources = [f"browser-evidence={browser_accessibility.get('summary')}"]
        if accessibility_status == "fail":
            quality_finding(
                findings,
                "accessibility_baseline",
                "high",
                "Browser accessibility baseline failed.",
                "Resolve accessibility failures from browser-evidence.json before handoff.",
                "browser-evidence.checks.accessibility_baseline",
                "fixer",
            )
        elif accessibility_status == "warning":
            for item in browser_evidence.get("findings", []):
                if isinstance(item, dict) and item.get("check") == "accessibility_baseline":
                    quality_finding(
                        findings,
                        "accessibility_baseline",
                        item.get("severity", "medium"),
                        item.get("summary", "Browser accessibility baseline has warnings."),
                        item.get("recommendation", "Resolve browser accessibility warnings before production handoff."),
                        item.get("source", "browser-evidence"),
                        "handoff",
                    )
    else:
        accessibility_status = evidence_status(accessibility_evidence)
        accessibility_sources = [str(accessibility_evidence)] if accessibility_evidence is not None else []
    if accessibility_status == "fail":
        accessibility_status = "warning"
        quality_finding(
            findings,
            "accessibility_baseline",
            "medium",
            "Accessibility baseline evidence is missing.",
            "Add keyboard, contrast, label, or screen-reader smoke evidence before production handoff.",
            "locked-spec.spec_evidence.accessibility",
            "handoff",
        )
    checks["accessibility_baseline"] = quality_check(
        accessibility_status,
        "Accessibility baseline evidence is present." if accessibility_status == "pass" else "Accessibility baseline is missing but not release-blocking in v0.",
        accessibility_sources,
    )

    proof_status = "pass"
    proof_gates = proof_bundle.get("gates")
    if isinstance(proof_gates, dict):
        for gate in ("ux_guard", "build", "review", "amendment", "integration"):
            if proof_gates.get(gate) != "pass":
                proof_status = "fail"
                quality_finding(
                    findings,
                    "proof_readiness",
                    "high",
                    f"Proof bundle gate `{gate}` is not pass.",
                    "Complete all upstream gates before final QA.",
                    f"proof-bundle.gates.{gate}",
                )
    else:
        proof_status = "fail"
        quality_finding(
            findings,
            "proof_readiness",
            "high",
            "Proof bundle gates are missing.",
            "Initialize or refresh proof-bundle.json before final handoff.",
            "proof-bundle.gates",
        )
    checks["proof_readiness"] = quality_check(
        proof_status,
        "Proof bundle prerequisite gates are ready." if proof_status == "pass" else "Proof bundle is not ready.",
        [f"{key}={value}" for key, value in proof_gates.items()] if isinstance(proof_gates, dict) else [],
    )

    critical_findings = sum(1 for item in findings if item["severity"] == "critical")
    high_findings = sum(1 for item in findings if item["severity"] == "high")
    medium_findings = sum(1 for item in findings if item["severity"] == "medium")
    low_findings = sum(1 for item in findings if item["severity"] == "low")
    report_status = "fail" if critical_findings or high_findings else "pass"
    if report_status == "pass":
        next_route = "lodestar-dock"
    elif any(item["owner"] == "amend-advisor" for item in findings if item["severity"] in QUALITY_FAIL_SEVERITIES):
        next_route = "lodestar-course-correct"
    elif sum(1 for item in findings if item["severity"] in QUALITY_FAIL_SEVERITIES) >= 3:
        next_route = "lodestar-debrief"
    else:
        next_route = "lodestar-eva"

    return {
        "run_id": run_id,
        "spec_id": spec_id,
        "status": report_status,
        "upstream_source": {
            "repo": "gstack",
            "adapter": "lodestar-quality-gate",
            "paths": [
                "third_party/upstream/gstack/qa",
                "third_party/upstream/gstack/qa-only",
                "third_party/upstream/gstack/ship",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-proof",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-browser-test",
            ],
        },
        "checks": checks,
        "findings": findings,
        "metrics": {
            "total_findings": len(findings),
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "medium_findings": medium_findings,
            "low_findings": low_findings,
            "check_pass_count": sum(1 for item in checks.values() if item["status"] == "pass"),
            "check_fail_count": sum(1 for item in checks.values() if item["status"] == "fail"),
            "check_warning_count": sum(1 for item in checks.values() if item["status"] == "warning"),
            "check_not_applicable_count": sum(1 for item in checks.values() if item["status"] == "not_applicable"),
        },
        "next_route": next_route,
        "artifacts": artifacts
        or {
            "locked_spec": "locked-spec.json",
            "execution_plan": "execution-plan.json",
            "build_evidence": "build-evidence.json",
            "review_report": "review-report.json",
            "ux_lock": "shape-lock.md",
            "browser_evidence": "browser-evidence.json",
            "proof_bundle": "proof-bundle.json",
        },
    }


def severity_rank(severity: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 0)


def highest_severity(severities: list[str]) -> str:
    valid = [severity for severity in severities if severity in QUALITY_SEVERITIES]
    if not valid:
        return "medium"
    return sorted(valid, key=severity_rank, reverse=True)[0]


def ce_owner_from_route(route_owner: str | None) -> str:
    if route_owner == "amend-advisor":
        return "amend-advisor"
    if route_owner == "human":
        return "fixer"
    if route_owner in {"fixer", "debrief"}:
        return route_owner
    return "fixer"


def collect_task_attempt_evidence(execution_plan: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    tasks = execution_plan.get("tasks")
    if not isinstance(tasks, list):
        return evidence
    for task in tasks:
        if not isinstance(task, dict):
            continue
        attempts = task.get("attempts")
        if not isinstance(attempts, dict):
            continue
        repeated_fields = [
            ("build_attempts", "build attempts"),
            ("review_attempts", "review attempts"),
            ("fix_attempts", "fix attempts"),
            ("ce_cycles", "CE cycles"),
        ]
        repeated = [f"{label}={attempts.get(field)}" for field, label in repeated_fields if isinstance(attempts.get(field), int) and attempts.get(field) >= 2]
        if isinstance(attempts.get("ce_cycles"), int) and attempts.get("ce_cycles") >= 1 and not repeated:
            repeated.append(f"CE cycles={attempts.get('ce_cycles')}")
        if repeated:
            evidence.append(
                {
                    "task_id": task.get("task_id", "unknown-task"),
                    "summary": f"Task {task.get('task_id', 'unknown-task')} shows repeated or escalated failure: {', '.join(repeated)}.",
                    "source": f"execution-plan.tasks.{task.get('task_id', 'unknown-task')}.attempts",
                }
            )
    return evidence


def add_ce_cluster(
    clusters: dict[str, dict[str, Any]],
    kind: str,
    severity: str,
    summary: str,
    evidence: str,
    owner: str,
) -> None:
    key = kind
    cluster = clusters.setdefault(
        key,
        {
            "id": f"CE-{len(clusters) + 1:03d}",
            "kind": kind,
            "severity": severity,
            "summary": summary,
            "evidence": [],
            "owners": [],
        },
    )
    cluster["severity"] = highest_severity([cluster["severity"], severity])
    if summary not in cluster["summary"]:
        cluster["summary"] = summary if len(summary) > len(cluster["summary"]) else cluster["summary"]
    if evidence not in cluster["evidence"]:
        cluster["evidence"].append(evidence)
    if owner not in cluster["owners"]:
        cluster["owners"].append(owner)


def build_debrief(
    run_id: str,
    spec: dict[str, Any],
    execution_plan: dict[str, Any],
    review_report: dict[str, Any],
    quality_report: dict[str, Any] | None = None,
    build_evidence: dict[str, Any] | None = None,
    artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    clusters: dict[str, dict[str, Any]] = {}
    spec_id = spec.get("id") if non_empty_string(spec.get("id")) else execution_plan.get("spec_id", "unknown-spec")
    build_evidence = build_evidence or {}
    quality_report = quality_report or {}

    if build_evidence.get("status") == "fail":
        add_ce_cluster(
            clusters,
            "build_failure",
            "high",
            "Build evidence failed before review could safely pass.",
            "build-evidence.status=fail",
            "fixer",
        )

    if review_report.get("status") == "rejected":
        add_ce_cluster(
            clusters,
            "review_reject",
            "high",
            "Reviewer rejected the implementation and the failure needs synthesis before another retry.",
            "review-report.status=rejected",
            "fixer",
        )
    if review_report.get("reviewer_read_only") is not True or review_report.get("code_edits_made") is not False:
        add_ce_cluster(
            clusters,
            "review_integrity",
            "critical",
            "Reviewer integrity contract was violated.",
            "review-report reviewer_read_only/code_edits_made",
            "debrief",
        )
    review_findings = review_report.get("findings")
    if isinstance(review_findings, list):
        for index, item in enumerate(review_findings):
            if not isinstance(item, dict):
                continue
            if item.get("owner") == "amend-advisor":
                add_ce_cluster(
                    clusters,
                    "product_intent_conflict",
                    "high",
                    item.get("summary", "Review finding may change product intent."),
                    f"review-report.findings[{index}]",
                    "amend-advisor",
                )
            elif item.get("severity") in {"P0", "P1"} or item.get("requires_verification") is True:
                add_ce_cluster(
                    clusters,
                    "review_reject",
                    "high" if item.get("severity") in {"P0", "P1"} else "medium",
                    item.get("summary", "Review finding requires another verified fix loop."),
                    f"review-report.findings[{index}]",
                    ce_owner_from_route(item.get("owner")),
                )

    if quality_report.get("status") == "fail":
        add_ce_cluster(
            clusters,
            "quality_failure",
            "high",
            "Quality gate failed and must be translated into a fix strategy before retrying.",
            "quality-report.status=fail",
            "fixer",
        )
    quality_findings = quality_report.get("findings")
    if isinstance(quality_findings, list):
        for index, item in enumerate(quality_findings):
            if not isinstance(item, dict):
                continue
            if item.get("severity") not in QUALITY_FAIL_SEVERITIES:
                continue
            kind = "product_intent_conflict" if item.get("owner") == "amend-advisor" else "quality_failure"
            add_ce_cluster(
                clusters,
                kind,
                item.get("severity", "high"),
                item.get("summary", "Quality finding requires synthesis."),
                f"quality-report.findings[{index}]",
                ce_owner_from_route(item.get("owner")),
            )

    for item in collect_task_attempt_evidence(execution_plan):
        add_ce_cluster(
            clusters,
            "repeated_failure",
            "high",
            item["summary"],
            item["source"],
            "debrief",
        )

    if not clusters:
        add_ce_cluster(
            clusters,
            "repeated_failure",
            "medium",
            "CE was invoked without concrete repeated-failure evidence.",
            "missing CE trigger evidence",
            "fixer",
        )
        status = "blocked"
    else:
        status = "ready"

    cluster_list = list(clusters.values())
    trigger_cluster = sorted(cluster_list, key=lambda item: severity_rank(item["severity"]), reverse=True)[0]
    may_change_product_intent = any(cluster["kind"] == "product_intent_conflict" or "amend-advisor" in cluster["owners"] for cluster in cluster_list)
    if may_change_product_intent:
        return_route = "lodestar-course-correct"
        strategy_owner = "amend-advisor"
    else:
        return_route = "lodestar-eva"
        strategy_owner = "fixer"

    evidence_lines = [evidence for cluster in cluster_list for evidence in cluster["evidence"]]
    what_did_not_work = []
    if review_report.get("status") == "rejected":
        what_did_not_work.append("Prior implementation reached reviewer but did not satisfy review criteria.")
    if build_evidence.get("status") == "fail":
        what_did_not_work.append("Prior implementation did not produce passing build evidence.")
    if quality_report.get("status") == "fail":
        what_did_not_work.append("Prior implementation did not satisfy final Quality/QA gate.")
    if any(cluster["kind"] == "repeated_failure" for cluster in cluster_list):
        what_did_not_work.append("Retrying without changing the fix hypothesis has already escalated into CE.")

    learning_status = "required" if any(cluster["kind"] == "repeated_failure" for cluster in cluster_list) else "not-needed"
    learning_key = "-".join(sorted({cluster["kind"] for cluster in cluster_list}))[:80]
    if not learning_key:
        learning_key = "ce-no-trigger"
    prevention_rule = "Before retrying, state the root-cause hypothesis, the evidence that supports it, and the verification command that will disprove it."

    return {
        "run_id": run_id,
        "spec_id": str(spec_id),
        "status": status,
        "upstream_source": {
            "repo": "compound-engineering-plugin",
            "adapter": "lodestar-debrief",
            "paths": [
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-debug",
                "third_party/upstream/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound/references/schema.yaml",
                "third_party/upstream/gstack/learn",
                "third_party/upstream/gstack/context-save",
            ],
        },
        "trigger": {
            "kind": trigger_cluster["kind"],
            "severity": trigger_cluster["severity"],
            "summary": trigger_cluster["summary"],
            "source": trigger_cluster["evidence"][0],
        },
        "failure_clusters": cluster_list,
        "root_cause_hypothesis": {
            "summary": "The current failure loop is likely caused by an untested assumption in the previous fix strategy, not by a lack of another retry.",
            "confidence": "medium" if status == "ready" else "low",
            "supporting_evidence": evidence_lines or ["CE invoked without sufficient evidence."],
        },
        "what_did_not_work": what_did_not_work,
        "next_fix_strategy": {
            "owner": strategy_owner,
            "steps": [
                "Pick one failure cluster and write the smallest falsifiable fix hypothesis.",
                "Change only the code or spec surface needed for that hypothesis.",
                "Run the build, regression smoke, and review evidence that previously failed.",
                "Return through implementer/fixer, then builder, then reviewer before QA or handoff.",
            ],
        },
        "verification_plan": [
            "Rerun the failed build or smoke command.",
            "Refresh review-report.json with reviewer_read_only=true and code_edits_made=false.",
            "Refresh quality-report.json before handoff.",
        ],
        "learning_note": {
            "status": learning_status,
            "key": learning_key,
            "summary": "Capture this repeated failure pattern if the next fix succeeds.",
            "prevention_rule": prevention_rule,
        },
        "intent_impact": {
            "may_change_product_intent": may_change_product_intent,
            "amendment_required": may_change_product_intent,
            "reason": "Failure evidence is owned by amend advisor." if may_change_product_intent else "Failure can be handled inside the locked implementation intent.",
        },
        "return_route": return_route,
        "forbidden_routes": sorted(CE_FORBIDDEN_ROUTES),
        "artifacts": artifacts
        or {
            "review_report": "review-report.json",
            "quality_report": "quality-report.json",
            "execution_plan": "execution-plan.json",
            "build_evidence": "build-evidence.json",
        },
    }


def render_debrief_brief(synthesis: dict[str, Any]) -> str:
    clusters = synthesis.get("failure_clusters", [])
    cluster_lines = []
    if isinstance(clusters, list):
        for cluster in clusters:
            if isinstance(cluster, dict):
                cluster_lines.append(f"- {cluster.get('kind')}: {cluster.get('summary')} ({cluster.get('severity')})")
    what_did_not_work = synthesis.get("what_did_not_work", [])
    failed_lines = [f"- {item}" for item in what_did_not_work] if isinstance(what_did_not_work, list) else []
    strategy = synthesis.get("next_fix_strategy", {})
    steps = strategy.get("steps", []) if isinstance(strategy, dict) else []
    step_lines = [f"- {step}" for step in steps] if isinstance(steps, list) else []
    verification = synthesis.get("verification_plan", [])
    verification_lines = [f"- {item}" for item in verification] if isinstance(verification, list) else []
    intent = synthesis.get("intent_impact", {})
    learning = synthesis.get("learning_note", {})
    hypothesis = synthesis.get("root_cause_hypothesis", {})

    return "\n".join(
        [
            "# CE Brief",
            "",
            f"Run: {synthesis.get('run_id')}",
            f"Spec: {synthesis.get('spec_id')}",
            f"Status: {synthesis.get('status')}",
            f"Return route: {synthesis.get('return_route')}",
            "",
            "## Trigger",
            "",
            f"{synthesis.get('trigger', {}).get('summary', 'No trigger summary.')}",
            "",
            "## Failure Clusters",
            "",
            *(cluster_lines or ["- No concrete failure cluster was found."]),
            "",
            "## Root-Cause Hypothesis",
            "",
            f"{hypothesis.get('summary', 'No hypothesis recorded.')}",
            "",
            "## What Did Not Work",
            "",
            *(failed_lines or ["- No prior failed attempt was recorded."]),
            "",
            "## Next Fix Strategy",
            "",
            *(step_lines or ["- Return to fixer with a falsifiable hypothesis."]),
            "",
            "## Verification Plan",
            "",
            *(verification_lines or ["- Refresh build, review, and quality evidence."]),
            "",
            "## Intent Impact",
            "",
            f"Amendment required: {intent.get('amendment_required')}",
            f"Reason: {intent.get('reason')}",
            "",
            "## Learning Note",
            "",
            f"Status: {learning.get('status')}",
            f"Key: {learning.get('key')}",
            f"Prevention: {learning.get('prevention_rule')}",
            "",
        ]
    )


def build_spec_gate_report(
    spec: dict[str, Any],
    ux_lock_text: str = "",
    decision_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    categories: dict[str, dict[str, str]] = {}

    spec_id = spec.get("id") if non_empty_string(spec.get("id")) else "unknown-spec"

    goals_ok = non_empty_string_list(spec.get("goals"))
    non_goals_ok = non_empty_string_list(spec.get("non_goals"))
    functional_status = "pass" if goals_ok and non_goals_ok else "fail"
    if not goals_ok:
        finding(findings, "functional_scope", "high", "Locked Spec goals are missing or empty.", "Add concrete v1 goals before task split.", "locked-spec.goals")
    if not non_goals_ok:
        finding(findings, "functional_scope", "medium", "Locked Spec non-goals are missing or empty.", "Add explicit non-goals to prevent scope drift.", "locked-spec.non_goals")
    categories["functional_scope"] = {
        "status": functional_status,
        "summary": category_summary(functional_status, "Goals and non-goals are explicit.", "Functional scope is underspecified."),
    }

    data_status = evidence_status(explicit_evidence(spec, "data_model"))
    if data_status == "fail":
        finding(findings, "data_model", "medium", "No explicit data model evidence was provided.", "Add data model notes or mark data model as not_applicable with a reason.", "locked-spec.spec_evidence.data_model")
    categories["data_model"] = {
        "status": data_status,
        "summary": category_summary(data_status, "Data model evidence is present.", "Data model evidence is missing.", "Data model is explicitly not applicable."),
    }

    product_shape = spec.get("product_shape")
    ux_status = "pass"
    if not isinstance(product_shape, dict):
        ux_status = "fail"
        finding(findings, "ux_flow", "critical", "Product shape object is missing.", "Return to UX preview and product lock before spec gate.", "locked-spec.product_shape")
    else:
        if product_shape.get("approved_preview") is not True:
            ux_status = "fail"
            finding(findings, "ux_flow", "critical", "Approved UI/UX preview is missing.", "Get explicit wireframe, design-system, and final UI/UX approval before locking the spec.", "locked-spec.product_shape.approved_preview")
        for field in ("primary_user", "first_screen", "core_flow", "approval_source"):
            if not non_empty_string(product_shape.get(field)):
                ux_status = "fail"
                finding(findings, "ux_flow", "high", f"Product shape field `{field}` is missing.", f"Fill product_shape.{field} before task split.", f"locked-spec.product_shape.{field}")
        if not non_empty_string_list(product_shape.get("ux_principles")):
            ux_status = "fail"
            finding(findings, "ux_flow", "high", "UX principles are missing.", "Add UX principles that implementation must preserve.", "locked-spec.product_shape.ux_principles")
    if ux_lock_text.strip() and "Approved" not in ux_lock_text:
        ux_status = "fail"
        finding(findings, "ux_flow", "high", "UX lock exists but does not contain approval evidence.", "Record approved wireframe, design-system, and final UI/UX evidence in shape-lock.md.", "ux-lock")
    if decision_log is not None and len(decision_log) > 0 and accepted_decision_count(decision_log) == 0:
        ux_status = "fail"
        finding(findings, "ux_flow", "high", "Decision log has no accepted decisions.", "Record the accepted UX/product decisions before task split.", "decision-log")
    categories["ux_flow"] = {
        "status": ux_status,
        "summary": category_summary(ux_status, "Approved product shape and UX evidence are present.", "UX/product-shape evidence is incomplete."),
    }

    nfr_status = evidence_status(explicit_evidence(spec, "non_functional_quality"))
    if nfr_status == "fail":
        finding(findings, "non_functional_quality", "medium", "No explicit non-functional quality evidence was provided.", "Add measurable quality constraints or mark not_applicable with a reason.", "locked-spec.spec_evidence.non_functional_quality")
    categories["non_functional_quality"] = {
        "status": nfr_status,
        "summary": category_summary(nfr_status, "Non-functional quality evidence is present.", "Non-functional quality is underspecified.", "Non-functional quality is explicitly not applicable."),
    }

    integration_status = evidence_status(explicit_evidence(spec, "integrations"))
    if integration_status == "fail":
        finding(findings, "integrations", "medium", "No explicit integration evidence was provided.", "Add integration/dependency notes or mark not_applicable with a reason.", "locked-spec.spec_evidence.integrations")
    categories["integrations"] = {
        "status": integration_status,
        "summary": category_summary(integration_status, "Integration evidence is present.", "Integration evidence is missing.", "Integrations are explicitly not applicable."),
    }

    edge_status = evidence_status(explicit_evidence(spec, "edge_failure"))
    if edge_status == "fail":
        finding(findings, "edge_failure", "medium", "No explicit edge/failure handling evidence was provided.", "Add edge cases and expected failure behavior before implementation.", "locked-spec.spec_evidence.edge_failure")
    categories["edge_failure"] = {
        "status": edge_status,
        "summary": category_summary(edge_status, "Edge/failure handling evidence is present.", "Edge/failure handling is underspecified.", "Edge/failure handling is explicitly not applicable."),
    }

    constraints_status = evidence_status(explicit_evidence(spec, "constraints_tradeoffs"))
    if constraints_status == "fail":
        finding(findings, "constraints_tradeoffs", "medium", "No explicit constraints/tradeoffs evidence was provided.", "Document constraints, tradeoffs, or rejected alternatives.", "locked-spec.spec_evidence.constraints_tradeoffs")
    categories["constraints_tradeoffs"] = {
        "status": constraints_status,
        "summary": category_summary(constraints_status, "Constraints/tradeoffs evidence is present.", "Constraints/tradeoffs are underspecified.", "Constraints/tradeoffs are explicitly not applicable."),
    }

    terminology_status = evidence_status(explicit_evidence(spec, "terminology"))
    if terminology_status == "fail":
        finding(findings, "terminology", "medium", "No explicit terminology evidence was provided.", "Add canonical terms or glossary notes to prevent agent drift.", "locked-spec.spec_evidence.terminology")
    categories["terminology"] = {
        "status": terminology_status,
        "summary": category_summary(terminology_status, "Terminology evidence is present.", "Terminology is underspecified.", "Terminology is explicitly not applicable."),
    }

    completion_status = "pass"
    success_criteria = spec.get("success_criteria")
    scenarios = spec.get("acceptance_scenarios")
    if not isinstance(success_criteria, list) or not success_criteria:
        completion_status = "fail"
        finding(findings, "completion_signals", "critical", "Success criteria are missing.", "Add testable success criteria before task split.", "locked-spec.success_criteria")
    elif any(not isinstance(item, dict) or item.get("testable") is not True for item in success_criteria):
        completion_status = "fail"
        finding(findings, "completion_signals", "high", "One or more success criteria are not testable.", "Make every success criterion explicitly testable.", "locked-spec.success_criteria")
    if not isinstance(scenarios, list) or not scenarios:
        completion_status = "fail"
        finding(findings, "completion_signals", "critical", "Acceptance scenarios are missing.", "Add Given/When/Then acceptance scenarios.", "locked-spec.acceptance_scenarios")
    else:
        for index, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict) or any(not non_empty_string(scenario.get(field)) for field in ("given", "when", "then")):
                completion_status = "fail"
                finding(findings, "completion_signals", "high", f"Acceptance scenario {index + 1} is incomplete.", "Fill given/when/then for every acceptance scenario.", f"locked-spec.acceptance_scenarios[{index}]")
    decision_policy = spec.get("decision_policy")
    if not isinstance(decision_policy, list):
        completion_status = "fail"
        finding(findings, "completion_signals", "high", "Decision policy is missing.", "Add all Lodestar decision policy classes.", "locked-spec.decision_policy")
    else:
        classes = {item.get("class") for item in decision_policy if isinstance(item, dict)}
        missing_classes = sorted(DECISION_CLASSES - classes)
        if missing_classes:
            completion_status = "fail"
            finding(findings, "completion_signals", "high", f"Decision policy is missing classes: {', '.join(missing_classes)}.", "Add complete decision policy coverage.", "locked-spec.decision_policy")
    categories["completion_signals"] = {
        "status": completion_status,
        "summary": category_summary(completion_status, "Success criteria, acceptance scenarios, and decision policy are testable.", "Completion signals are incomplete."),
    }

    placeholder_status = "pass"
    spec_text = json.dumps(spec, ensure_ascii=False, sort_keys=True)
    found_placeholders = [marker for marker in SPEC_GATE_PLACEHOLDERS if marker in spec_text]
    if found_placeholders:
        placeholder_status = "fail"
        finding(
            findings,
            "placeholders",
            "high",
            f"Locked Spec contains unresolved placeholder markers: {', '.join(found_placeholders)}.",
            "Resolve placeholders before product lock or route back to clarification.",
            "locked-spec",
        )
    categories["placeholders"] = {
        "status": placeholder_status,
        "summary": category_summary(placeholder_status, "No unresolved placeholder markers were found.", "Unresolved placeholders remain in the Locked Spec."),
    }

    critical_findings = sum(1 for item in findings if item["severity"] == "critical")
    high_findings = sum(1 for item in findings if item["severity"] == "high")
    medium_findings = sum(1 for item in findings if item["severity"] == "medium")
    low_findings = sum(1 for item in findings if item["severity"] == "low")
    report_status = "fail" if critical_findings or high_findings else "pass"
    product_intent_categories = {"functional_scope", "ux_flow", "completion_signals", "placeholders"}
    intent_affecting_failure = any(
        item["severity"] in {"critical", "high"} and item["category"] in product_intent_categories for item in findings
    )
    next_route = "lodestar-stages" if report_status == "pass" else ("lodestar-course-correct" if intent_affecting_failure else "lodestar-lock")

    return {
        "spec_id": spec_id,
        "status": report_status,
        "upstream_source": {
            "repo": "spec-kit",
            "adapter": "lodestar-checklist",
            "paths": [
                "third_party/upstream/spec-kit/templates/commands/clarify.md",
                "third_party/upstream/spec-kit/templates/commands/analyze.md",
                "third_party/upstream/spec-kit/templates/commands/specify.md",
                "third_party/upstream/spec-kit/templates/checklist-template.md",
            ],
        },
        "categories": categories,
        "findings": findings,
        "metrics": {
            "total_findings": len(findings),
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "medium_findings": medium_findings,
            "low_findings": low_findings,
            "category_pass_count": sum(1 for item in categories.values() if item["status"] == "pass"),
            "category_fail_count": sum(1 for item in categories.values() if item["status"] == "fail"),
            "category_not_applicable_count": sum(1 for item in categories.values() if item["status"] == "not_applicable"),
        },
        "next_route": next_route,
    }
