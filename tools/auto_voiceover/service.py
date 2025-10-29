# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from tools.auto_voiceover.config import AutoVoiceoverConfig, load_config
from tools.auto_voiceover.parser import ScriptParser
from tools.auto_voiceover.planner import PlanResult, TaskPlanner, VoiceoverTask
from tools.auto_voiceover.postprocess import ManifestConfig, PostProcessor
from tools.auto_voiceover.tts_runner import (
    ExecutionOptions,
    ExecutionSummary,
    IndexTTS2Executor,
    TaskResult,
    CancelledError,
)


def run_voiceover(
    script_path: Path | str,
    config_path: Path | str,
    out_root: Path | str,
    *,
    voice_root: Optional[Path | str] = None,
    language: Optional[str] = None,
    dry_run: bool = False,
    model_dir: Optional[Path | str] = None,
    model_config: Optional[Path | str] = None,
    device: Optional[str] = None,
    use_fp16: bool = False,
    use_deepspeed: bool = False,
    use_cuda_kernel: Optional[bool] = None,
    force: bool = False,
    max_text_tokens: int = 120,
    default_interval: float = 0.2,
    emo_alpha: float = 1.0,
    verbose: bool = False,
    speaker_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    speaker_filter: Optional[List[str]] = None,
    cancel_checker: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """执行自动配音流程，返回执行结果详情。"""

    script_path = Path(script_path).expanduser().resolve()
    config_path = Path(config_path).expanduser().resolve()
    out_root = Path(out_root).expanduser().resolve()

    try:
        out_root.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"无法创建输出目录 {out_root}: {exc}")

    if not script_path.exists():
        raise FileNotFoundError(f"脚本文件不存在: {script_path}")
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = load_config(config_path)
    if voice_root:
        voice_root_path = Path(voice_root).expanduser().resolve()
        config.voice_root = str(voice_root_path)
    else:
        if config.voice_root:
            voice_root_path = Path(config.voice_root)
            if not voice_root_path.is_absolute():
                voice_root_path = (config_path.parent / voice_root_path).resolve()
            config.voice_root = str(voice_root_path)
        else:
            voice_root_path = None

    if speaker_overrides:
        for speaker_id, overrides in speaker_overrides.items():
            if speaker_id not in config.speakers:
                continue
            profile = config.speakers[speaker_id]
            if "emo_mode" in overrides:
                profile.emo_mode = overrides.get("emo_mode") or None
            if "emo_text" in overrides:
                profile.emo_text = overrides.get("emo_text") or None
            if "emo_alpha" in overrides:
                try:
                    profile.emo_alpha = float(overrides.get("emo_alpha")) if overrides.get("emo_alpha") not in (None, "") else None
                except (TypeError, ValueError):
                    pass
            if "interval_silence" in overrides:
                try:
                    profile.interval_silence = float(overrides.get("interval_silence")) if overrides.get("interval_silence") not in (None, "") else None
                except (TypeError, ValueError):
                    pass
            if "emo_audio" in overrides:
                audio_value = overrides.get("emo_audio")
                profile.emo_audio = str(audio_value) if audio_value else None
            if "emo_vector" in overrides and overrides.get("emo_vector"):
                try:
                    vector = overrides.get("emo_vector")
                    if isinstance(vector, str):
                        vector = json.loads(vector)
                    profile.emo_vector = [float(v) for v in vector]
                except (Exception):  # noqa: BLE001
                    pass

    parser = ScriptParser(language=language)
    parse_result = parser.parse_file(script_path)

    planner = TaskPlanner(
        config=config,
        output_root=out_root,
        language=language,
        config_root=config_path.parent,
    )
    plan_result = planner.plan(parse_result)

    valid_speakers = {sid.lower() for sid in config.speakers.keys()}
    missing_segments = getattr(plan_result, "skipped_segments", [])
    missing_speakers = sorted({segment.speaker for segment in missing_segments})
    missing_segments_payload = [
        {
            "sequence_id": segment.sequence_id,
            "chapter_id": segment.chapter_id,
            "speaker": segment.speaker,
            "text": segment.text,
            "emotion_hint": getattr(segment, "emotion_hint", None),
        }
        for segment in missing_segments
    ]

    filter_set: Optional[set[str]] = None
    if speaker_filter:
        filter_set = {sid.lower() for sid in speaker_filter}
        filter_set &= valid_speakers

    allowed_set = filter_set if filter_set is not None else valid_speakers

    tasks = [
        task
        for task in plan_result.tasks
        if task.segment.speaker.lower() in allowed_set
    ]

    if not tasks:
        return {
            "dry_run": dry_run,
            "segment_count": 0,
            "speakers": sorted(config.speakers.keys()),
            "output_root": str(plan_result.output_root),
            "episode_title": plan_result.episode_title,
            "segments": [],
            "voice_root": str(voice_root_path) if voice_root_path else None,
            "progress_log": [],
            "status": "ok",
            "cancelled": False,
            "message": "未找到匹配的主持人片段",
            "missing_speakers": missing_speakers,
            "missing_segments": missing_segments_payload,
        }

    filtered_plan = plan_result
    if tasks is not plan_result.tasks:
        filtered_plan = PlanResult(
            tasks=tasks,
            output_root=plan_result.output_root,
            episode_title=plan_result.episode_title,
            skipped_segments=plan_result.skipped_segments,
        )

    segments_payload = [
        {
            "sequence_id": task.sequence_id,
            "chapter_id": task.segment.chapter_id,
            "chapter_title": task.segment.chapter_title,
            "speaker": task.segment.speaker,
            "text": task.segment.text,
            "emotion_hint": getattr(task.segment, "emotion_hint", None),
            "directives": [directive.__dict__ for directive in task.segment.directives],
            "output_path": str(task.output_path.relative_to(plan_result.output_root))
            if task.output_path.is_relative_to(plan_result.output_root)
            else str(task.output_path),
        }
        for task in tasks
    ]

    if dry_run:
        return {
            "dry_run": True,
            "segment_count": len(segments_payload),
            "speakers": sorted(config.speakers.keys()),
            "output_root": str(filtered_plan.output_root),
            "episode_title": filtered_plan.episode_title,
            "segments": segments_payload,
            "voice_root": str(voice_root_path) if voice_root_path else None,
            "progress_log": [],
            "status": "ok",
            "cancelled": False,
            "missing_speakers": missing_speakers,
            "missing_segments": missing_segments_payload,
        }

    if model_dir is None:
        raise ValueError("执行真实合成时必须指定 model_dir")

    model_dir = Path(model_dir).expanduser().resolve()
    if not model_dir.exists():
        raise FileNotFoundError(f"模型目录不存在: {model_dir}")

    model_config_path = Path(model_config).expanduser().resolve() if model_config else None

    executor = IndexTTS2Executor(
        config=config,
        config_root=config_path.parent,
        model_dir=model_dir,
        cfg_path=model_config_path,
        device=device,
        use_fp16=use_fp16,
        use_deepspeed=use_deepspeed,
        use_cuda_kernel=use_cuda_kernel,
    )
    exec_options = ExecutionOptions(
        force=force,
        verbose=verbose,
        max_text_tokens=max_text_tokens,
        default_interval_s=default_interval,
        emo_alpha=emo_alpha,
    )
    progress_log: List[str] = []

    def _progress_cb(index: int, total: int, task: VoiceoverTask, result: TaskResult) -> None:
        status_symbol = "✅" if result.status == "completed" else ("⏭" if result.status == "skipped" else "⚠")
        progress_log.append(f"{index}/{total} {status_symbol} {task.sequence_id} -> {result.status}")

    cancelled = False
    try:
        summary = executor.run(
            tasks,
            exec_options,
            progress_callback=_progress_cb,
            cancel_checker=cancel_checker,
        )
    except CancelledError as exc:
        cancelled = True
        summary = ExecutionSummary(results=exc.results)

    manifest_path: Optional[Path] = None
    manifest_payload: Optional[Dict[str, Any]] = None
    if not cancelled:
        manifest_config = ManifestConfig(output_root=filtered_plan.output_root)
        post_processor = PostProcessor(manifest_config)
        manifest_path, manifest_payload = post_processor.emit_manifest(filtered_plan, summary)

    return {
        "dry_run": False,
        "output_root": str(filtered_plan.output_root),
        "episode_title": filtered_plan.episode_title,
        "segment_count": len(tasks),
        "summary": {
            "total": len(summary.results),
            "completed": summary.completed,
            "skipped": summary.skipped,
            "failed": summary.failed,
        },
        "manifest_path": str(manifest_path) if manifest_path else None,
        "manifest": manifest_payload,
        "segments": segments_payload,
        "voice_root": str(voice_root_path) if voice_root_path else None,
        "speaker_overrides": speaker_overrides or {},
        "progress_log": progress_log,
        "cancelled": cancelled,
        "status": "ok",
        "missing_speakers": missing_speakers,
        "missing_segments": missing_segments_payload,
    }


__all__ = ["run_voiceover"]
