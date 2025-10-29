# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from flask import Flask, flash, redirect, render_template, request, url_for, jsonify

from tools.auto_voiceover.config import load_config
from tools.auto_voiceover.parser import ScriptParser
from tools.auto_voiceover.service import run_voiceover

app = Flask(__name__)
app.config["SECRET_KEY"] = "auto-voiceover-secret"

PROJECT_ROOT = Path(__file__).parent
DEFAULT_BASE_DIR = (PROJECT_ROOT / "tools" / "test_input").resolve()
DEFAULT_MODEL_DIR = (PROJECT_ROOT / "checkpoints").resolve()
PRESET_EMO_TEXTS = [
    "温暖而富有激情",
    "沉稳而富有感染力",
    "愉悦、充满微笑",
    "平静而理性",
    "激动、充满力量",
    "悲伤且克制",
    "紧张而快速",
    "轻松、悠闲的谈话",
]
EMO_VECTOR_KEYS = [
    "高兴",
    "愤怒",
    "悲伤",
    "恐惧",
    "反感",
    "低落",
    "惊讶",
    "自然",
]

current_job: Dict[str, bool] = {"running": False, "cancel": False}


def ensure_config_file(config_path: Path, base_dir: Path, voice_root_value: Optional[str]) -> Path:
    config_path = config_path.expanduser().resolve()
    if config_path.exists():
        return config_path

    voice_root = Path(voice_root_value).expanduser().resolve() if voice_root_value else (base_dir / "voice-reference")
    if not voice_root.exists():
        return config_path

    speakers: Dict[str, Any] = {}
    for subdir in sorted(voice_root.iterdir()):
        if not subdir.is_dir():
            continue
        voice_files = []
        for ext in ("*.wav", "*.mp3", "*.m4a", "*.flac", "*.ogg"):
            voice_files.extend(subdir.glob(ext))
        if not voice_files:
            continue
        voice_prompt = str(voice_files[0].resolve())
        speakers[subdir.name] = {
            "voice_prompt": voice_prompt,
            "emo_mode": "text",
            "emo_text": "",
            "emo_alpha": 0.8,
            "interval_silence": 0.2,
        }

    if not speakers:
        return config_path

    config_data = {
        "default_tts": {"top_p": 0.8, "temperature": 0.8},
        "voice_root": str(voice_root.resolve()),
        "auto_speaker_defaults": {
            "emo_mode": "text",
            "emo_text": "",
            "emo_alpha": 0.8,
            "interval_silence": 0.2,
        },
        "speakers": speakers,
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f, allow_unicode=True)
    return config_path


def discover_scripts(base_dir: Path) -> List[Path]:
    scripts_dir = base_dir / "scripts"
    if not scripts_dir.exists():
        return []
    return sorted(p for p in scripts_dir.glob("*.md") if p.is_file())


def infer_language(script_name: str) -> Optional[str]:
    lowered = script_name.lower()
    if lowered.endswith("_en") or lowered.endswith("-en") or "_en_" in lowered:
        return "en"
    if lowered.endswith("_cn") or lowered.endswith("-cn") or "_cn_" in lowered or "zh" in lowered:
        return "zh"
    return None


def build_output_root(base_dir: Path, script_path: Path) -> Path:
    return base_dir / "DUB" / script_path.stem


def _get_param(name: str, default: Optional[str] = None) -> Optional[str]:
    value = request.form.get(name)
    if value in (None, ""):
        value = request.args.get(name)
    return value if value not in (None, "") else default


def _get_flag(name: str, default: bool = False) -> bool:
    value = _get_param(name)
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "on", "yes"}


def _collect_base_settings() -> Dict[str, str]:
    base_settings: Dict[str, str] = {}
    base_settings["base_dir"] = _get_param("base_dir", str(DEFAULT_BASE_DIR))
    base_settings["model_dir"] = _get_param("model_dir", str(DEFAULT_MODEL_DIR))
    base_settings["voice_root"] = _get_param("voice_root", "") or ""
    base_settings["config_path"] = _get_param("config_path", "") or ""
    base_settings["device"] = _get_param("device", "") or ""
    base_settings["max_text_tokens"] = _get_param("max_text_tokens", "120") or "120"
    base_settings["default_interval"] = _get_param("default_interval", "0.2") or "0.2"
    base_settings["emo_alpha"] = _get_param("emo_alpha", "1.0") or "1.0"
    base_settings["fp16"] = "1" if _get_flag("fp16", True) else "0"
    base_settings["force"] = "1" if _get_flag("force", False) else "0"
    base_settings["use_cuda_kernel"] = "1" if _get_flag("use_cuda_kernel", False) else "0"
    base_settings["deepspeed"] = "1" if _get_flag("deepspeed", False) else "0"
    return base_settings


def _load_speaker_settings(config_path: Path, base_settings: Dict[str, str]) -> List[Dict[str, str]]:
    speakers: List[Dict[str, str]] = []
    if not config_path.exists():
        return speakers
    try:
        config_preview = load_config(config_path)
    except Exception as exc:  # noqa: BLE001
        flash(f"加载配置失败: {exc}", "error")
        return speakers

    for speaker_id, profile in config_preview.speakers.items():
        raw_vec = _get_param(f"emo_vector_{speaker_id}")
        if not raw_vec:
            vec_from_profile = getattr(profile, "emo_vector", None)
            raw_vec = json.dumps(vec_from_profile) if vec_from_profile else ""
        vector_list: List[float] = [0.0] * len(EMO_VECTOR_KEYS)
        if raw_vec:
            try:
                parsed = json.loads(raw_vec)
                if isinstance(parsed, list):
                    vector_list = [float(parsed[i]) if i < len(parsed) else 0.0 for i in range(len(EMO_VECTOR_KEYS))]
            except Exception:  # noqa: BLE001
                pass

        info = {
            "id": speaker_id,
            "emo_mode": _get_param(f"emo_mode_{speaker_id}") or (profile.emo_mode or ""),
            "emo_text": _get_param(f"emo_text_{speaker_id}") or (profile.emo_text or ""),
            "emo_alpha": _get_param(f"emo_alpha_{speaker_id}") or (str(profile.emo_alpha) if profile.emo_alpha is not None else base_settings["emo_alpha"]),
            "interval_silence": _get_param(f"interval_silence_{speaker_id}") or (str(profile.interval_silence) if profile.interval_silence is not None else base_settings["default_interval"]),
            "emo_audio": _get_param(f"emo_audio_{speaker_id}") or (profile.emo_audio or ""),
            "emo_vector": raw_vec or "",
            "emo_vector_list": vector_list,
        }
        speakers.append(info)
    return speakers


@app.route("/", methods=["GET", "POST"])
def index():
    base_settings = _collect_base_settings()
    base_dir = Path(base_settings["base_dir"]).expanduser().resolve()
    model_dir = Path(base_settings["model_dir"]).expanduser().resolve()
    voice_root_param = base_settings["voice_root"] or None
    config_candidate = Path(base_settings["config_path"]) if base_settings.get("config_path") else base_dir / "speakers.yaml"
    config_path = ensure_config_file(config_candidate, base_dir, voice_root_param)
    base_settings["config_path"] = str(config_path)

    scripts: List[Path] = []
    if base_dir.exists():
        scripts = discover_scripts(base_dir)
        if not scripts:
            flash("未在 scripts/ 目录下找到 Markdown 脚本", "warning")
    else:
        flash(f"基础目录不存在: {base_dir}", "warning")

    speakers_settings = _load_speaker_settings(config_path, base_settings)

    result_data = None
    error_message: Optional[str] = None
    speaker_overrides: Dict[str, Dict[str, str]] = {
        info["id"]: {
            "emo_mode": info.get("emo_mode"),
            "emo_text": info.get("emo_text"),
            "emo_alpha": info.get("emo_alpha"),
            "interval_silence": info.get("interval_silence"),
            "emo_audio": info.get("emo_audio"),
            "emo_vector": info.get("emo_vector"),
        }
        for info in speakers_settings
    }

    if request.method == "POST" and request.form.get("action") in {"run", "dry_run"}:
        script_value = request.form.get("script_path")
        if not script_value:
            flash("请选择要运行的脚本", "warning")
            return redirect(url_for("index", base_dir=str(base_dir), model_dir=str(model_dir)))

        script_path = Path(script_value).expanduser().resolve()
        if not script_path.exists():
            error_message = f"脚本文件不存在: {script_path}"
        else:
            voice_root_path = Path(voice_root_param).expanduser().resolve() if voice_root_param else (base_dir / "voice-reference")
            language = request.form.get("language")
            if language in (None, "", "auto"):
                language = infer_language(script_path.stem)

            action = request.form.get("action")
            dry_run = action == "dry_run"

            out_root_input = request.form.get("out_root")
            out_root = Path(out_root_input).expanduser().resolve() if out_root_input else build_output_root(base_dir, script_path)

            try:
                result_data = run_voiceover(
                    script_path=script_path,
                    config_path=config_path,
                    out_root=out_root,
                    voice_root=voice_root_path,
                    language=language,
                    dry_run=dry_run,
                    model_dir=model_dir,
                    model_config=None,
                    device=request.form.get("device") or base_settings["device"] or None,
                    use_fp16=bool(request.form.get("fp16") or base_settings["fp16"] == "1"),
                    use_deepspeed=bool(request.form.get("deepspeed") or base_settings["deepspeed"] == "1"),
                    use_cuda_kernel=bool(request.form.get("use_cuda_kernel") or base_settings["use_cuda_kernel"] == "1"),
                    force=bool(request.form.get("force") or base_settings["force"] == "1"),
                    max_text_tokens=int(request.form.get("max_text_tokens") or base_settings["max_text_tokens"] or 120),
                    default_interval=float(request.form.get("default_interval") or base_settings["default_interval"] or 0.2),
                    emo_alpha=float(request.form.get("emo_alpha") or base_settings["emo_alpha"] or 1.0),
                    verbose=False,
                    speaker_overrides=speaker_overrides,
                )
                flash("任务执行完成" if not dry_run else "Dry-run 完成", "success")
            except Exception as exc:  # noqa: BLE001
                error_message = str(exc)

    scripts_info = []
    parser = ScriptParser()
    valid_speakers = {s["id"].lower(): s["id"] for s in speakers_settings}
    for script in scripts:
        speakers: List[str] = []
        try:
            parse_res = parser.parse_file(script)
            raw = {seg.speaker for seg in parse_res.segments}
            speakers = sorted({valid_speakers.get(s.lower(), s) for s in raw if s.lower() in valid_speakers})
        except Exception as exc:  # noqa: BLE001
            flash(f"解析脚本失败 {script}: {exc}", "error")
        if not speakers:
            speakers = sorted(valid_speakers.values())
        scripts_info.append(
            {
                "path": script,
                "language": infer_language(script.stem) or "",
                "out_root": build_output_root(base_dir, script),
                "speakers": speakers,
            }
        )

    settings_query = {
        **base_settings,
        **{f"emo_mode_{s['id']}": s["emo_mode"] for s in speakers_settings},
        **{f"emo_text_{s['id']}": s["emo_text"] for s in speakers_settings},
        **{f"emo_alpha_{s['id']}": s["emo_alpha"] for s in speakers_settings},
        **{f"interval_silence_{s['id']}": s["interval_silence"] for s in speakers_settings},
    }

    speakers_map = {s["id"]: s for s in speakers_settings}

    context = {
        "base_dir": base_dir,
        "model_dir": model_dir,
        "voice_root": Path(voice_root_param).expanduser().resolve() if voice_root_param else base_dir / "voice-reference",
        "config_path": config_path,
        "scripts": scripts_info,
        "result": result_data,
        "result_json": json.dumps(result_data, ensure_ascii=False, indent=2) if result_data else None,
        "error_message": error_message,
        "settings": {
            "device": base_settings["device"],
            "fp16": base_settings["fp16"] == "1",
            "force": base_settings["force"] == "1",
            "use_cuda_kernel": base_settings["use_cuda_kernel"] == "1",
            "deepspeed": base_settings["deepspeed"] == "1",
            "max_text_tokens": base_settings["max_text_tokens"],
            "default_interval": base_settings["default_interval"],
            "emo_alpha": base_settings["emo_alpha"],
        },
        "speakers_settings": speakers_settings,
        "speakers_map": speakers_map,
        "settings_url": url_for("settings_page", **{k: v for k, v in settings_query.items() if v not in (None, "")}),
        "settings_query_json": json.dumps(settings_query),
        "preset_emo_texts": PRESET_EMO_TEXTS,
        "vector_keys": EMO_VECTOR_KEYS,
        "vector_zero": [0.0] * len(EMO_VECTOR_KEYS),
    }
    return render_template("auto_voiceover.html", **context)


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    base_settings = _collect_base_settings()
    base_dir = Path(base_settings["base_dir"]).expanduser().resolve()
    model_dir = Path(base_settings["model_dir"]).expanduser().resolve()
    voice_root_param = base_settings["voice_root"] or ""
    config_candidate = Path(base_settings["config_path"]) if base_settings.get("config_path") else base_dir / "speakers.yaml"
    config_path = ensure_config_file(config_candidate, base_dir, voice_root_param or None)
    base_settings["config_path"] = str(config_path)

    speakers_settings = _load_speaker_settings(config_path, base_settings)

    if request.method == "POST":
        base_settings["base_dir"] = request.form.get("base_dir", base_settings["base_dir"])
        base_settings["model_dir"] = request.form.get("model_dir", base_settings["model_dir"])
        base_settings["voice_root"] = request.form.get("voice_root", voice_root_param)
        base_settings["config_path"] = request.form.get("config_path", base_settings["config_path"])
        base_settings["device"] = request.form.get("device", base_settings["device"])
        base_settings["max_text_tokens"] = request.form.get("max_text_tokens", base_settings["max_text_tokens"])
        base_settings["default_interval"] = request.form.get("default_interval", base_settings["default_interval"])
        base_settings["emo_alpha"] = request.form.get("emo_alpha", base_settings["emo_alpha"])
        base_settings["fp16"] = "1" if request.form.get("fp16") else "0"
        base_settings["force"] = "1" if request.form.get("force") else "0"
        base_settings["use_cuda_kernel"] = "1" if request.form.get("use_cuda_kernel") else "0"
        base_settings["deepspeed"] = "1" if request.form.get("deepspeed") else "0"

        base_dir = Path(base_settings["base_dir"]).expanduser().resolve()
        voice_root_current = base_settings.get("voice_root") or ""
        config_candidate = Path(base_settings["config_path"]) if base_settings.get("config_path") else base_dir / "speakers.yaml"
        config_path = ensure_config_file(config_candidate, base_dir, voice_root_current or None)
        base_settings["config_path"] = str(config_path)
        speakers_settings = _load_speaker_settings(config_path, base_settings)

        redirect_params = {k: v for k, v in base_settings.items() if v not in (None, "")}
        for speaker in speakers_settings:
            redirect_params[f"emo_mode_{speaker['id']}"] = request.form.get(f"emo_mode_{speaker['id']}", speaker["emo_mode"])
            redirect_params[f"emo_text_{speaker['id']}"] = request.form.get(f"emo_text_{speaker['id']}", speaker["emo_text"])
            redirect_params[f"emo_alpha_{speaker['id']}"] = request.form.get(f"emo_alpha_{speaker['id']}", speaker["emo_alpha"])
            redirect_params[f"interval_silence_{speaker['id']}"] = request.form.get(f"interval_silence_{speaker['id']}", speaker["interval_silence"])
            redirect_params[f"emo_audio_{speaker['id']}"] = request.form.get(f"emo_audio_{speaker['id']}", speaker["emo_audio"])
            redirect_params[f"emo_vector_{speaker['id']}"] = request.form.get(f"emo_vector_{speaker['id']}", speaker["emo_vector"])

        return redirect(url_for("index", **redirect_params))

    settings_query = {
        **base_settings,
        **{f"emo_mode_{s['id']}": s["emo_mode"] for s in speakers_settings},
        **{f"emo_text_{s['id']}": s["emo_text"] for s in speakers_settings},
        **{f"emo_alpha_{s['id']}": s["emo_alpha"] for s in speakers_settings},
        **{f"interval_silence_{s['id']}": s["interval_silence"] for s in speakers_settings},
    }

    context = {
        "base_dir": base_dir,
        "model_dir": model_dir,
        "voice_root": voice_root_param,
        "config_path": config_path,
        "settings": base_settings,
        "speakers_settings": speakers_settings,
        "settings_query": settings_query,
        "preset_emo_texts": PRESET_EMO_TEXTS,
        "vector_keys": EMO_VECTOR_KEYS,
        "vector_zero": [0.0] * len(EMO_VECTOR_KEYS),
    }
    return render_template("auto_voiceover_settings.html", **context)


@app.post("/run")
def run_endpoint():
    global current_job
    if current_job.get("running"):
        return jsonify({"status": "error", "message": "已有任务正在执行"}), 409

    data = request.get_json(silent=True) or {}
    script_path = data.get("script_path")
    config_path = data.get("config_path")
    out_root = data.get("out_root")
    if not script_path or not config_path or not out_root:
        return jsonify({"status": "error", "message": "缺少必要参数"}), 400

    base_dir_value = data.get("base_dir")
    if base_dir_value:
        base_dir_path = Path(base_dir_value).expanduser().resolve()
    else:
        base_dir_path = Path(config_path).expanduser().resolve().parent
    config_path = ensure_config_file(Path(config_path), base_dir_path, data.get("voice_root"))

    speakers_raw = data.get("script_speakers", "")
    speakers_list = [s for s in speakers_raw.split(",") if s]

    raw_filter = data.get("speaker_filter")
    if isinstance(raw_filter, list):
        filter_list = [s for s in raw_filter if s]
    elif isinstance(raw_filter, str):
        filter_list = [s for s in raw_filter.split(",") if s]
    else:
        filter_list = []
    if not filter_list:
        filter_list = speakers_list

    overrides: Dict[str, Dict[str, Any]] = {}
    for sid in filter_list:
        overrides[sid] = {
            "emo_mode": data.get(f"emo_mode_{sid}"),
            "emo_text": data.get(f"emo_text_{sid}"),
            "emo_alpha": data.get(f"emo_alpha_{sid}"),
            "interval_silence": data.get(f"interval_silence_{sid}"),
            "emo_audio": data.get(f"emo_audio_{sid}"),
            "emo_vector": data.get(f"emo_vector_{sid}"),
        }

    current_job["running"] = True
    current_job["cancel"] = False

    def cancel_checker() -> bool:
        return current_job.get("cancel", False)

    try:
        result = run_voiceover(
            script_path=script_path,
            config_path=config_path,
            out_root=out_root,
            voice_root=data.get("voice_root") or None,
            language=data.get("language") or None,
            dry_run=(data.get("action") == "dry_run"),
            model_dir=data.get("model_dir") or None,
            model_config=None,
            device=data.get("device") or None,
            use_fp16=data.get("fp16") in (True, "1", "true", "on"),
            use_deepspeed=data.get("deepspeed") in (True, "1", "true", "on"),
            use_cuda_kernel=data.get("use_cuda_kernel") in (True, "1", "true", "on"),
            force=data.get("force") in (True, "1", "true", "on"),
            max_text_tokens=int(data.get("max_text_tokens") or 120),
            default_interval=float(data.get("default_interval") or 0.2),
            emo_alpha=float(data.get("emo_alpha") or 1.0),
            verbose=False,
            speaker_overrides=overrides,
            speaker_filter=filter_list,
            cancel_checker=cancel_checker,
        )
        result_status = "cancelled" if result.get("cancelled") else "ok"
        result["status"] = result_status
        return jsonify(result)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        current_job["cancel"] = False
        current_job["running"] = False


@app.post("/cancel")
def cancel_endpoint():
    global current_job
    if not current_job.get("running"):
        return jsonify({"status": "idle"})
    current_job["cancel"] = True
    return jsonify({"status": "cancelling"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=False)
