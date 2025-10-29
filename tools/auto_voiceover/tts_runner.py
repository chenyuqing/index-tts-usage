# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from indextts.infer_v2 import IndexTTS2

from tools.auto_voiceover.config import AutoVoiceoverConfig
from tools.auto_voiceover.planner import VoiceoverTask


@dataclass
class ExecutionOptions:
    """执行阶段的全局参数。"""

    force: bool = False
    verbose: bool = False
    max_text_tokens: int = 120
    default_interval_s: float = 0.2
    emo_alpha: float = 1.0


@dataclass
class TaskResult:
    task: VoiceoverTask
    status: str  # completed | skipped | failed
    output_path: Optional[Path]
    duration: float
    error: Optional[str] = None


@dataclass
class ExecutionSummary:
    results: List[TaskResult]

    @property
    def completed(self) -> int:
        return sum(1 for r in self.results if r.status == "completed")

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")


class CancelledError(RuntimeError):
    def __init__(self, message: str, results: List[TaskResult]) -> None:
        super().__init__(message)
        self.results = results


class IndexTTS2Executor:
    """封装 IndexTTS2 推理流程，提供批量执行接口。"""

    def __init__(
        self,
        config: AutoVoiceoverConfig,
        config_root: Path,
        model_dir: Path,
        cfg_path: Optional[Path] = None,
        device: Optional[str] = None,
        use_fp16: bool = False,
        use_deepspeed: bool = False,
        use_cuda_kernel: Optional[bool] = None,
    ) -> None:
        self.config = config
        self.config_root = config_root
        self.model_dir = model_dir
        self.cfg_path = cfg_path or (model_dir / "config.yaml")
        self.device = device
        self.use_fp16 = use_fp16
        self.use_deepspeed = use_deepspeed
        self.use_cuda_kernel = use_cuda_kernel
        self._model: Optional[IndexTTS2] = None

    # --------------------------------------------------------------------- public

    def run(
        self,
        tasks: Iterable[VoiceoverTask],
        options: ExecutionOptions,
        progress_callback: Optional[Callable[[int, int, VoiceoverTask, TaskResult], None]] = None,
        cancel_checker: Optional[Callable[[], bool]] = None,
    ) -> ExecutionSummary:
        results: List[TaskResult] = []

        task_list = list(tasks)
        total = len(task_list)
        for index, task in enumerate(task_list, start=1):
            try:
                result = self._run_single(task, options)
            except Exception as exc:  # noqa: BLE001
                result = TaskResult(
                    task=task,
                    status="failed",
                    output_path=None,
                    duration=0.0,
                    error=str(exc),
                )
            results.append(result)
            if progress_callback is not None:
                try:
                    progress_callback(index, total, task, result)
                except Exception:
                    pass
            if cancel_checker is not None and cancel_checker():
                raise CancelledError("cancelled", results)

        return ExecutionSummary(results=results)

    # ------------------------------------------------------------------ internals

    def _run_single(self, task: VoiceoverTask, options: ExecutionOptions) -> TaskResult:
        output_path = task.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists() and not options.force:
            if options.verbose:
                print(f"[skip] {task.sequence_id} 已存在，跳过 ({output_path})")
            return TaskResult(task=task, status="skipped", output_path=output_path, duration=0.0)

        model = self._ensure_model()
        speaker = task.speaker_profile
        voice_prompt = self._resolve_path(speaker.voice_prompt)
        if not voice_prompt.exists():
            raise FileNotFoundError(f"voice_prompt 不存在: {voice_prompt}")

        emo_kwargs = self._build_emotion_kwargs(task, options)
        gen_kwargs = self._build_generation_kwargs(task)
        interval_ms = self._determine_interval_ms(task, options)

        start = time.perf_counter()
        model.infer(
            spk_audio_prompt=str(voice_prompt),
            text=task.segment.text,
            output_path=str(output_path),
            interval_silence=interval_ms,
            verbose=options.verbose,
            max_text_tokens_per_segment=options.max_text_tokens,
            **emo_kwargs,
            **gen_kwargs,
        )
        duration = time.perf_counter() - start
        if options.verbose:
            print(f"[done] {task.sequence_id} -> {output_path} ({duration:.2f}s)")

        return TaskResult(task=task, status="completed", output_path=output_path, duration=duration)

    def _ensure_model(self) -> IndexTTS2:
        if self._model is None:
            self._model = IndexTTS2(
                cfg_path=str(self.cfg_path),
                model_dir=str(self.model_dir),
                use_fp16=self.use_fp16,
                device=self.device,
                use_deepspeed=self.use_deepspeed,
                use_cuda_kernel=self.use_cuda_kernel,
            )
        return self._model

    def _build_emotion_kwargs(self, task: VoiceoverTask, options: ExecutionOptions) -> dict:
        speaker = task.speaker_profile
        emo_mode = (speaker.emo_mode or "").lower()
        base_alpha = speaker.emo_alpha if getattr(speaker, "emo_alpha", None) is not None else options.emo_alpha
        segment_hint = getattr(task.segment, "emotion_hint", None)
        segment_hint = segment_hint.strip() if isinstance(segment_hint, str) else None

        if emo_mode == "audio":
            emo_audio = speaker.emo_audio or speaker.voice_prompt
            emo_audio_path = self._resolve_path(emo_audio)
            if not emo_audio_path.exists():
                raise FileNotFoundError(f"emo_audio_prompt 不存在: {emo_audio_path}")
            return {"emo_audio_prompt": str(emo_audio_path), "emo_alpha": base_alpha}

        if emo_mode == "vector":
            if not speaker.emo_vector:
                raise ValueError(f"speaker '{speaker.speaker_id}' 未提供 emo_vector")
            return {"emo_vector": list(speaker.emo_vector), "emo_alpha": base_alpha}

        if emo_mode == "text":
            emo_text = segment_hint or speaker.emo_text or task.segment.text
            return {"use_emo_text": True, "emo_text": emo_text, "emo_alpha": base_alpha}

        if segment_hint:
            return {"use_emo_text": True, "emo_text": segment_hint, "emo_alpha": base_alpha}

        # 默认情况下不传 emotion 参数；IndexTTS2 会复用音色参考音频。
        return {}

    def _build_generation_kwargs(self, task: VoiceoverTask) -> dict:
        payload = self.config.default_tts.to_dict()
        payload.update(task.speaker_profile.tts_params.to_dict())
        # 清理潜在的 None 或无效值。
        cleaned = {}
        for key, value in payload.items():
            if value is None:
                continue
            if key == "top_k" and int(value) <= 0:
                cleaned[key] = None
            else:
                cleaned[key] = value

        cleaned.setdefault("do_sample", True)
        cleaned.setdefault("repetition_penalty", 10.0)
        cleaned.setdefault("max_mel_tokens", 1500)
        cleaned.setdefault("num_beams", 3)
        return cleaned

    def _determine_interval_ms(self, task: VoiceoverTask, options: ExecutionOptions) -> int:
        interval_s = task.speaker_profile.interval_silence
        if interval_s is None:
            interval_s = options.default_interval_s
        interval_s = max(0.0, float(interval_s))
        return int(round(interval_s * 1000.0))

    def _resolve_path(self, value: Optional[str]) -> Path:
        if value is None:
            raise ValueError("路径参数不能为空")
        path = Path(value)
        if not path.is_absolute():
            path = (self.config_root / path).resolve()
        return path


__all__ = ["IndexTTS2Executor", "ExecutionOptions", "ExecutionSummary", "TaskResult"]
