# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class Directive:
    """表示脚本中的舞台指令或非语音提示。"""

    type: str
    value: str
    raw: str = ""


@dataclass
class Segment:
    """主持人单条台词，结合章节信息与指令。"""

    chapter_id: str
    chapter_title: Optional[str]
    sequence_id: str
    speaker: str
    text: str
    directives: List[Directive] = field(default_factory=list)
    source_path: Optional[Path] = None
    line_number: Optional[int] = None
    emotion_hint: Optional[str] = None


@dataclass
class ParseResult:
    """解析结果，包含所有 segment 及元信息。"""

    segments: List[Segment]
    episode_title: Optional[str] = None


class ScriptParser:
    """
    将 Markdown 播客脚本解析为 Segment 列表。

    默认适配示例脚本格式：
    - 一级标题 `#` 视为节目标题，占位用，不生成章节。
    - 二级标题 `##` 表示章节，第一章编号为 ch00。
    - 台词格式：`**Speaker：** 内容` 或 `**Speaker:** 内容`。
    - 括号行（中英文括号）视为指令，附着在最近一条台词上；若无台词，则记录为章节级指令。
    """

    SPEECH_PATTERN = re.compile(r"^\*\*(?P<speaker>[^*]+?)[：:]\*\*\s*(?P<content>.*)$")
    DIRECTIVE_PATTERN = re.compile(r"^[（(](?P<content>.+?)[)）]\s*$")
    EMOTION_PATTERN = re.compile(
        r"^\s*[【\[]\s*(?:情绪|emotion|tone|mood|style)\s*[=:：]\s*(?P<value>[^】\]]+)\s*[】\]]\s*",
        re.IGNORECASE,
    )

    def __init__(self, language: Optional[str] = None) -> None:
        self.language = language

    def parse_file(self, path: Path) -> ParseResult:
        content = path.read_text(encoding="utf-8")
        result = self.parse(content.splitlines(), source=path)
        return result

    def parse(self, lines: Iterable[str], source: Optional[Path] = None) -> ParseResult:
        chapter_idx = -1
        chapter_id = "ch00"
        chapter_title: Optional[str] = None
        episode_title: Optional[str] = None
        segment_counter = 0
        segments: List[Segment] = []
        pending_directives: List[Directive] = []
        current_segment: Optional[Segment] = None

        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            if self._is_horizontal_rule(line):
                # 水平分割线仅用于视觉分割，继续读取。
                continue

            heading_level, heading_text = self._match_heading(line)
            if heading_level:
                if heading_level == 1:
                    # 节目标题，重置章节指针但不编号。
                    chapter_idx = -1
                    episode_title = heading_text
                    chapter_title = None
                    chapter_id = "ch00"
                    segment_counter = 0
                    pending_directives.clear()
                    current_segment = None
                elif heading_level == 2:
                    chapter_idx += 1
                    chapter_id = f"ch{chapter_idx:02d}"
                    chapter_title = heading_text
                    segment_counter = 0
                    pending_directives.clear()
                    current_segment = None
                else:
                    # 更深层级暂按正文处理。
                    pass
                continue

            speech_match = self.SPEECH_PATTERN.match(line)
            if speech_match:
                speaker = speech_match.group("speaker").strip()
                raw_text = speech_match.group("content").strip()
                text, emotion_hint = self._extract_emotion(raw_text)
                segment_counter += 1
                sequence_id = f"{chapter_id}-{segment_counter:02d}"
                current_segment = Segment(
                    chapter_id=chapter_id,
                    chapter_title=chapter_title,
                    sequence_id=sequence_id,
                    speaker=self._normalize_speaker(speaker),
                    text=text,
                    directives=pending_directives.copy(),
                    source_path=source,
                    line_number=line_number,
                    emotion_hint=emotion_hint,
                )
                segments.append(current_segment)
                pending_directives.clear()
                continue

            directive_match = self.DIRECTIVE_PATTERN.match(line)
            if directive_match:
                directive_text = directive_match.group("content").strip()
                directive = Directive(type="stage", value=directive_text, raw=raw_line)
                if current_segment:
                    current_segment.directives.append(directive)
                else:
                    pending_directives.append(directive)
                continue

            # 处理段落续写：附加到最近的 segment。
            if current_segment is None:
                # 没有当前台词，视为章节级备注。
                pending_directives.append(Directive(type="note", value=line, raw=raw_line))
            else:
                clean_line, extra_hint = self._extract_emotion(line)
                if extra_hint:
                    if current_segment.emotion_hint:
                        current_segment.emotion_hint = f"{current_segment.emotion_hint}; {extra_hint}"
                    else:
                        current_segment.emotion_hint = extra_hint
                if clean_line:
                    if current_segment.text:
                        current_segment.text += " " + clean_line
                    else:
                        current_segment.text = clean_line

        return ParseResult(segments=segments, episode_title=episode_title)

    @staticmethod
    def _normalize_speaker(name: str) -> str:
        return name.strip().replace(" ", "_").lower()

    @staticmethod
    def _match_heading(line: str) -> tuple[int, str]:
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not match:
            return 0, ""
        hashes, text = match.groups()
        return len(hashes), text.strip()

    @staticmethod
    def _is_horizontal_rule(line: str) -> bool:
        return line in ("---", "***", "___")

    def _extract_emotion(self, text: str) -> tuple[str, Optional[str]]:
        if not text:
            return text, None

        remaining = text
        hints: List[str] = []
        while True:
            match = self.EMOTION_PATTERN.match(remaining)
            if not match:
                break
            value = match.group("value").strip()
            if value:
                hints.append(value)
            remaining = remaining[match.end() :]
        return remaining.lstrip(), "; ".join(hints) if hints else None


__all__ = ["ScriptParser", "Segment", "Directive", "ParseResult"]
