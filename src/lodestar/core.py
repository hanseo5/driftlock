"""Core helpers: errors, JSON/text IO, the browser HTML parser, validation primitives."""
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

from .constants import *  # noqa: F401,F403


class LodestarError(Exception):
    """Raised when Lodestar validation fails."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LodestarError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LodestarError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {key.lower(): value or "" for key, value in attrs}


class BrowserEvidenceHTMLParser(HTMLParser):
    """Extracts stable page signals without depending on a browser package."""

    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.text_chunks: list[str] = []
        self.heading_parts: list[str] = []
        self.heading_stack: list[str] = []
        self.button_stack: list[dict[str, Any]] = []
        self.input_attrs: list[dict[str, str]] = []
        self.label_for_ids: set[str] = set()
        self.html_lang = False
        self.links = 0
        self.buttons = 0
        self.buttons_without_name = 0
        self.inputs = 0
        self.inputs_without_label = 0
        self.images = 0
        self.images_without_alt = 0
        self.aria_labels = 0
        self._in_title = False
        self._suppressed_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = attrs_dict(attrs)
        if tag in {"script", "style", "noscript", "template"}:
            self._suppressed_depth += 1
            return
        if data.get("aria-label") or data.get("aria-labelledby"):
            self.aria_labels += 1
        if tag == "html" and non_empty_string(data.get("lang")):
            self.html_lang = True
        elif tag == "title":
            self._in_title = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_stack.append(tag)
            self.heading_parts.append("")
        elif tag == "a":
            self.links += 1
        elif tag == "img":
            self.images += 1
            if data.get("aria-hidden") != "true" and data.get("role") != "presentation" and not non_empty_string(data.get("alt")):
                self.images_without_alt += 1
        elif tag == "input":
            input_type = data.get("type", "text").lower()
            if input_type not in {"hidden", "submit", "button", "reset"}:
                self.inputs += 1
                self.input_attrs.append(data)
        elif tag == "label":
            if non_empty_string(data.get("for")):
                self.label_for_ids.add(str(data["for"]))
        elif tag == "button":
            self.buttons += 1
            self.button_stack.append({"attrs": data, "text": []})

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "template"} and self._suppressed_depth:
            self._suppressed_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self.heading_stack:
            self.heading_stack.pop()
        elif tag == "button" and self.button_stack:
            button = self.button_stack.pop()
            attrs = button["attrs"]
            text = " ".join(button["text"]).strip()
            if not text and not attrs.get("aria-label") and not attrs.get("title"):
                self.buttons_without_name += 1

    def handle_data(self, data: str) -> None:
        if self._suppressed_depth:
            return
        stripped = " ".join(data.split())
        if not stripped:
            return
        if self._in_title:
            self.title_parts.append(stripped)
        else:
            self.text_chunks.append(stripped)
        if self.heading_stack and self.heading_parts:
            self.heading_parts[-1] = " ".join([self.heading_parts[-1], stripped]).strip()
        if self.button_stack:
            self.button_stack[-1]["text"].append(stripped)

    def close(self) -> None:
        super().close()
        for input_attr in self.input_attrs:
            input_id = input_attr.get("id")
            labelled = (
                non_empty_string(input_attr.get("aria-label"))
                or non_empty_string(input_attr.get("aria-labelledby"))
                or non_empty_string(input_attr.get("title"))
                or (non_empty_string(input_id) and str(input_id) in self.label_for_ids)
            )
            if not labelled:
                self.inputs_without_label += 1

    def page(self) -> dict[str, Any]:
        text = " ".join(self.text_chunks)
        headings = [heading for heading in self.heading_parts if heading.strip()]
        return {
            "title": " ".join(self.title_parts).strip(),
            "text_sample": text[:500],
            "_text_search": text,
            "text_length": len(text),
            "headings": headings[:12],
            "links": self.links,
            "buttons": self.buttons,
            "buttons_without_name": self.buttons_without_name,
            "inputs": self.inputs,
            "inputs_without_label": self.inputs_without_label,
            "images": self.images,
            "images_without_alt": self.images_without_alt,
            "aria_labels": self.aria_labels,
            "html_lang": self.html_lang,
        }


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(non_empty_string(item) for item in value)


def fail_if_errors(errors: list[str]) -> None:
    if errors:
        raise LodestarError("\n".join(f"- {error}" for error in errors))
