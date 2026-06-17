"""CLI smoke test for the local voice stack — no browser, no mic, no oTree.

Runs the service legs directly so you can validate them before the browser:
    text -> TTS -> audio bytes -> STT -> text   (round trip)
    + a single LLM reply if VOICE_LLM_BACKEND=kit

Run it as a script (NOT `python -m`) so it does not import the oTree app
package; it loads services.py directly and only needs the deps for the
backends you actually enable.

    VOICE_TTS_BACKEND=say python Voice/smoketest.py "Ich fuehle mich angespannt."
    VOICE_STT_BACKEND=whisper-local VOICE_TTS_BACKEND=say \
        python Voice/smoketest.py "How are you feeling today?"
"""
import asyncio
import importlib.util
import pathlib
import sys

_spec = importlib.util.spec_from_file_location(
    "voice_services", pathlib.Path(__file__).resolve().parent / "services.py")
svc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(svc)


async def main(text: str):
    print(f"backends: STT={svc.STT_BACKEND}  LLM={svc.LLM_BACKEND}  TTS={svc.TTS_BACKEND}")
    print(f"text : {text!r}")

    audio, ext = await svc.synthesize(text, voice_id='')
    print(f"TTS  -> {len(audio)} bytes (.{ext or '-'})")
    if not audio:
        print("        (stub TTS — set VOICE_TTS_BACKEND=say or piper to get audio)")

    if audio and svc.STT_BACKEND == 'whisper-local':
        print(f"STT  <- {(await svc.transcribe(audio))!r}")
    elif svc.STT_BACKEND != 'whisper-local':
        print("        (STT stubbed — set VOICE_STT_BACKEND=whisper-local to transcribe)")

    if svc.LLM_BACKEND == 'kit':
        reply = await svc.generate_reply(
            [{'sender': 'user', 'text': text}],
            system_prompt='You are a brief, warm emotion-regulation coach.')
        print(f"LLM  -> {reply!r}")
    else:
        print("        (LLM stubbed — set VOICE_LLM_BACKEND=kit + OPENAI_URL to call your local model)")


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else 'Local voice stack test.'))
