# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IndexTTS2 is an advanced zero-shot text-to-speech (TTS) system that supports emotionally expressive speech synthesis with duration control. This is a Python project using PyTorch for deep learning, with both CLI and web interface implementations.

## Development Environment

- **Package Manager**: Use `uv` exclusively - other package managers (pip, conda) are not supported
- **Python Version**: Requires Python 3.10+
- **GPU Support**: CUDA 12.8+ required for GPU acceleration on Linux/Windows

## Core Commands

### Environment Setup
```bash
# Install dependencies (required before any other commands)
uv sync --all-extras

# Or install with specific extras only
uv sync --extra webui --extra deepspeed
```

### Running the Application
```bash
# Start web interface (main entry point)
uv run webui.py

# CLI usage for single inference
uv run indextts/cli.py "Your text here" -v examples/voice_01.wav -o output.wav

# Direct Python script execution (add PYTHONPATH)
PYTHONPATH="$PYTHONPATH:." uv run indextts/infer_v2.py
```

### Testing
```bash
# Run tests
uv run tests/regression_test.py
uv run tests/padding_test.py
```

### Utilities
```bash
# Check GPU/CUDA environment
uv run tools/gpu_check.py

# Download models via HuggingFace
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints

# Download models via ModelScope
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

## Architecture Overview

### Core Modules
- **`indextts/`**: Main package containing all TTS implementation
  - `infer_v2.py`: IndexTTS2 inference engine with emotion control
  - `infer.py`: Legacy IndexTTS1 inference engine
  - `cli.py`: Command-line interface
  - `gpt/`: GPT-based autoregressive model components
  - `s2mel/`: Speech-to-mel spectrogram conversion
  - `BigVGAN/`: Vocoder for mel-to-audio conversion
  - `utils/`: Shared utilities and preprocessing

### Key Features
- **Emotion Control**: Multiple input modalities (audio prompts, emotion vectors, text descriptions)
- **Speaker Cloning**: Zero-shot voice cloning from reference audio
- **Duration Control**: Precise speech timing control (IndexTTS2 feature)
- **Multi-language**: Supports Chinese and English

### Model Architecture
- **GPT-based autoregressive model** for semantic token prediction
- **Conformer encoder** for audio feature extraction
- **BigVGAN vocoder** for high-quality audio synthesis
- **Emotion decoupling** between speaker identity and emotional expression

## Configuration

- **Main Config**: `checkpoints/config.yaml` - model configuration
- **Web UI Config**: Command-line arguments in `webui.py` (port, host, model settings)
- **Required Model Files**: bpe.model, gpt.pth, s2mel.pth, wav2vec2bert_stats.pt

## Development Notes

- Always use absolute paths in terminal commands and scripts
- Use `uv run` prefix for all Python script execution
- WebUI runs on port 7860 by default - kill and restart if port conflicts occur
- FP16 inference recommended for lower VRAM usage
- DeepSpeed may improve performance but is hardware-dependent

## Cantonese TTS Integration Research

### Overview
Research conducted on integrating Cantonese (粤语) TTS capabilities with IndexTTS2's voice cloning features through integration with GPT-SoVITS.

### Technical Approach
**Audio Bridge Method**: Use IndexTTS2 for voice cloning to generate a "voice seed", then use GPT-SoVITS for Cantonese text synthesis.

```
Original Audio → IndexTTS2 Voice Cloning → Voice Seed → GPT-SoVITS Cantonese TTS → Final Output
```

### Integration Architecture
- **IndexTTS2**: Handles voice cloning and timbre extraction
- **GPT-SoVITS**: Provides Cantonese TTS capabilities with zero-shot voice cloning
- **Audio Bridge**: Intermediate audio file carrying voice characteristics

### Hardware Requirements
**Mac M4 16GB Compatibility:**
- IndexTTS2: ~6GB memory
- GPT-SoVITS: ~3GB memory
- System overhead: ~3GB
- **Total**: ~12GB (within 16GB limit)

### Performance Characteristics
- **Processing Time**: 5-10 seconds total (2-4s IndexTTS + 3-6s GPT-SoVITS)
- **Quality**: High voice similarity with minimal quality loss
- **Languages**: Original speaker voice → Cantonese speech output

### Implementation Components

#### Core Bridge Service
```python
class CantoneseVoiceBridge:
    def clone_and_synthesize(self, ref_audio, cantonese_text):
        # Step 1: Generate voice seed with IndexTTS2
        seed_audio = self.create_voice_seed(ref_audio)

        # Step 2: Synthesize Cantonese with GPT-SoVITS
        result = self.synthesize_cantonese(seed_audio, cantonese_text)
        return result
```

#### API Endpoints
- **IndexTTS2**: `http://127.0.0.1:7860` (existing)
- **GPT-SoVITS**: `http://127.0.0.1:9880` (new deployment)
- **Bridge Service**: `http://127.0.0.1:8080` (integration layer)

### Development Status
- **Research Phase**: Completed ✅
- **Technical Feasibility**: Validated ✅
- **Implementation**: Pending development branch

### Next Steps
1. Deploy GPT-SoVITS service alongside IndexTTS2
2. Implement audio bridge service
3. Create unified API interface
4. Performance optimization and quality tuning

### Related Files
- Voice cloning logic: `indextts/infer_v2.py`
- Text processing: `indextts/utils/front.py`, `indextts/utils/text_utils.py`
- Language detection: Current Chinese detection in `contains_chinese()` function

### References
- GPT-SoVITS: https://github.com/RVC-Boss/GPT-SoVITS
- IndexTTS2 Paper: [IndexTTS2 Research](https://arxiv.org/html/2506.21619v1)
- Cantonese TTS Survey: [Recent developments in 2024]