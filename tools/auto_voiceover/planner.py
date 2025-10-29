# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from tools.auto_voiceover.config import AutoVoiceoverConfig, SpeakerProfile
from tools.auto_voiceover.parser import ParseResult, Segment


@dataclass
class VoiceoverTask:
    """单条语音合成任务。"""

    sequence_id: str
    segment: Segment
    speaker_profile: SpeakerProfile
    output_path: Path
    episode_title: Optional[str]
    language: Optional[str] = None

    @property
    def chapter_dir(self) -> Path:
        return self.output_path.parent

    @property
    def speaker_id(self) -> str:
        return self.speaker_profile.speaker_id


@dataclass
class PlanResult:
    tasks: List[VoiceoverTask]
    output_root: Path
    episode_title: Optional[str]
    skipped_segments: List[Segment] = field(default_factory=list)


class TaskPlanner:
    """根据解析结果和配置生成可执行的合成任务队列。"""

    def __init__(
        self,
        config: AutoVoiceoverConfig,
        output_root: Path,
        language: Optional[str] = None,
        config_root: Optional[Path] = None,
    ) -> None:
        self.config = config
        self.output_root = output_root
        self.language = language
        self.config_root = config_root

    def plan(self, parse_result: ParseResult) -> PlanResult:
        tasks: List[VoiceoverTask] = []
        skipped: List[Segment] = []
        for segment in parse_result.segments:
            try:
                profile = self._resolve_speaker(segment.speaker)
            except KeyError:
                skipped.append(segment)
                continue
            output_path = self._build_output_path(segment)
            task = VoiceoverTask(
                sequence_id=segment.sequence_id,
                segment=segment,
                speaker_profile=profile,
                output_path=output_path,
                episode_title=parse_result.episode_title,
                language=self.language,
            )
            tasks.append(task)

        return PlanResult(
            tasks=tasks,
            output_root=self.output_root,
            episode_title=parse_result.episode_title,
            skipped_segments=skipped,
        )

    # --- helpers -----------------------------------------------------------------

    def _resolve_speaker(self, speaker_id: str) -> SpeakerProfile:
        candidates = [speaker_id]
        if self.language:
            candidates.append(f"{speaker_id}_{self.language}")
        for candidate in candidates:
            try:
                return self.config.resolve_speaker(candidate, base_path=self.config_root)
            except KeyError:
                continue
        raise KeyError(f"未在配置中找到 speaker '{speaker_id}'（尝试候选: {candidates}）")

    def _build_output_path(self, segment: Segment) -> Path:
        base = self.output_root
        chapter_dir = base / segment.chapter_id
        filename = f"{segment.sequence_id}-{segment.speaker}.wav"
        return chapter_dir / filename


__all__ = ["TaskPlanner", "PlanResult", "VoiceoverTask"]
