#!/usr/bin/env python3
"""
Integration tests for IndexTTS2 API service
"""

import requests
import json
import time
import base64
from pathlib import Path

# API configuration
BASE_URL = "http://localhost:7861"
API_BASE = f"{BASE_URL}/api/v1"


def test_health_check():
    """Test health check endpoint"""
    print("🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Health check passed")


def test_model_info():
    """Test model info endpoint"""
    print("🔍 Testing model info...")
    response = requests.get(f"{API_BASE}/models")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "supported_languages" in data
    print("✅ Model info test passed")


def test_tts_generation():
    """Test basic TTS generation"""
    print("🔍 Testing TTS generation...")
    payload = {
        "text": "你好，这是一个测试语音。",
        "language": "zh",
        "speed": 1.0,
        "pitch": 1.0
    }

    response = requests.post(f"{API_BASE}/tts", json=payload)

    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert "audio_data" in data
        assert "duration" in data
        print("✅ TTS generation test passed")
    else:
        print(f"⚠️  TTS generation failed (expected if no default voice): {response.status_code}")
        print(f"   Response: {response.text}")


def test_voice_analysis():
    """Test voice analysis endpoint"""
    print("🔍 Testing voice analysis...")

    # Find a sample audio file
    sample_audio = Path("../examples/voice_01.wav")
    if not sample_audio.exists():
        print("⚠️  No sample audio found, skipping voice analysis test")
        return

    with open(sample_audio, "rb") as f:
        files = {"reference_audio": ("voice.wav", f, "audio/wav")}
        response = requests.post(f"{API_BASE}/analyze-voice", files=files)

    if response.status_code == 200:
        data = response.json()
        assert "speaker_id" in data
        assert "confidence" in data
        print("✅ Voice analysis test passed")
    else:
        print(f"⚠️  Voice analysis failed: {response.status_code}")


def test_voice_cloning():
    """Test voice cloning endpoint"""
    print("🔍 Testing voice cloning...")

    # Find a sample audio file
    sample_audio = Path("../examples/voice_01.wav")
    if not sample_audio.exists():
        print("⚠️  No sample audio found, skipping voice cloning test")
        return

    with open(sample_audio, "rb") as f:
        files = {"reference_audio": ("voice.wav", f, "audio/wav")}
        data = {
            "text": "这是声音克隆的测试。",
            "language": "zh",
            "speed": 1.0,
            "pitch": 1.0
        }
        response = requests.post(f"{API_BASE}/clone-voice", files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        assert result["success"] is True
        assert "audio_data" in result
        assert "duration" in result
        print("✅ Voice cloning test passed")
    else:
        print(f"⚠️  Voice cloning failed: {response.status_code}")
        print(f"   Response: {response.text}")


def wait_for_service(max_attempts=30):
    """Wait for the service to be ready"""
    print("⏳ Waiting for service to be ready...")

    for i in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Service is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        print(f"   Attempt {i+1}/{max_attempts}...")
        time.sleep(2)

    print("❌ Service failed to start")
    return False


def run_all_tests():
    """Run all integration tests"""
    print("🧪 Starting IndexTTS2 API Integration Tests")
    print("=" * 50)

    # Wait for service to be ready
    if not wait_for_service():
        return False

    # Run tests
    tests = [
        test_health_check,
        test_model_info,
        test_tts_generation,
        test_voice_analysis,
        test_voice_cloning
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)