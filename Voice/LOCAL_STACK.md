# Fully-local voice stack (no API keys)

Run the whole turn loop on your machine — STT + LLM + TTS — with nothing leaving it.

| Leg | Local backend | Setup |
|-----|---------------|-------|
| STT | faster-whisper | `pip install -r requirements-local.txt` (model downloads on first use) |
| LLM | LM Studio (OpenAI-compatible) | load a model, **Start Server** in the Developer tab |
| TTS | macOS `say` (zero install) **or** piper | `say`: nothing; piper: `pip install piper-tts` + a voice `.onnx` |

## 1. `.env`

```
VOICE_STT_BACKEND=whisper-local
VOICE_LLM_BACKEND=kit
VOICE_TTS_BACKEND=say          # instant, robotic; use `piper` for real quality

# LLM via LM Studio
OPENAI_URL=http://localhost:1234/v1
OPENAI_MODEL=<model id from LM Studio's Developer tab>
OPENAI_KEY=lm-studio           # ignored by LM Studio, but must be non-empty

# faster-whisper accuracy/speed
WHISPER_MODEL=base             # or small / medium

# piper only (VOICE_TTS_BACKEND=piper)
# PIPER_VOICE=/path/to/de_DE-thorsten-medium.onnx
```

Restart `otree devserver` after editing `.env` — backends are read at startup.

## 2. Smoke test (no browser/mic)

Validates TTS + STT (and LLM if LM Studio is up) from the CLI:

```bash
# instant, zero-install (just TTS):
VOICE_TTS_BACKEND=say python Voice/smoketest.py "Ich fuehle mich angespannt."

# full local round trip once faster-whisper + LM Studio are ready:
VOICE_STT_BACKEND=whisper-local VOICE_LLM_BACKEND=kit VOICE_TTS_BACKEND=say \
    python Voice/smoketest.py "How are you feeling today?"
```

## 3. Browser

`otree devserver` → `/demo/Voice` → P1 → allow mic → spacebar to record/stop. You'll
see a real transcript, a real local-model reply, and hear the bot.

## Notes
- `say` is macOS-only and robotic — great for a first run; switch to a German **piper**
  voice (e.g. `de_DE-thorsten`) for quality, since the study is in German.
- STT + a large LLM + TTS run sequentially per turn, so latency adds up — `gpt-oss-20b`
  keeps turns snappy; a 70B is noticeably slower.
- This is a dev/experiment branch. For deployment the design targets the KIT `gpt-oss`
  endpoint; a fully-local stack is the GDPR-friendly alternative if the machine is capable.
