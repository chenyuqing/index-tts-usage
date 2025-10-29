# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from tools.auto_voiceover.planner import PlanResult, VoiceoverTask
from tools.auto_voiceover.tts_runner import ExecutionSummary, TaskResult


@dataclass
class ManifestConfig:
    output_root: Path
    manifest_path: Optional[Path] = None


class PostProcessor:
    """负责输出 manifest 及后续音频处理挂点的封装。"""

    def __init__(self, config: ManifestConfig) -> None:
        self.config = config

    def emit_manifest(self, plan: PlanResult, summary: ExecutionSummary) -> tuple[Path, dict]:
        manifest_path = self.config.manifest_path or (self.config.output_root / "manifest.json")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._build_manifest_payload(plan, summary, manifest_path)
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest_path, payload

    # ------------------------------------------------------------------ internals

    def _build_manifest_payload(
        self,
        plan: PlanResult,
        summary: ExecutionSummary,
        manifest_path: Path,
    ) -> dict:
        task_map = {result.task.sequence_id: result for result in summary.results}

        segments: List[dict] = []
        for task in plan.tasks:
            result = task_map.get(task.sequence_id)
            relative_output: Optional[str] = None
            if result and result.output_path is not None:
                try:
                    relative_output = str(result.output_path.relative_to(plan.output_root))
                except ValueError:
                    relative_output = str(result.output_path)

            segments.append(
                {
                    "sequence_id": task.sequence_id,
                    "chapter_id": task.segment.chapter_id,
                    "chapter_title": task.segment.chapter_title,
                    "speaker": task.segment.speaker,
                    "text": task.segment.text,
                    "emotion_hint": getattr(task.segment, "emotion_hint", None),
                    "directives": [directive.__dict__ for directive in task.segment.directives],
                    "status": result.status if result else "unknown",
                    "output_path": relative_output,
                    "duration": getattr(result, "duration", 0.0) if result else 0.0,
                    "error": result.error if result else None,
                }
            )

        payload = {
            "episode_title": plan.episode_title,
            "output_root": str(plan.output_root),
            "manifest_path": str(manifest_path),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total": len(summary.results),
                "completed": summary.completed,
                "skipped": summary.skipped,
                "failed": summary.failed,
            },
            "segments": segments,
            "skipped_segments": [
                {
                    "sequence_id": segment.sequence_id,
                    "chapter_id": segment.chapter_id,
                    "speaker": segment.speaker,
                    "text": segment.text,
                    "emotion_hint": getattr(segment, "emotion_hint", None),
                }
                for segment in getattr(plan, "skipped_segments", [])
            ],
        }
        return payload


__all__ = ["PostProcessor", "ManifestConfig"]
