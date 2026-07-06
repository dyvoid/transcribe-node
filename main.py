"""FastAPI server: OpenAI-compatible transcription API, engine control, hardware
info, and the operator UI. Run directly to start the service."""

import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from catalog import MODEL_CATALOG, recommend_model
from config import load_config
from engine import EngineManager, FasterWhisperEngine, TranscribeOptions
from formatting import to_srt, to_verbose_json, to_vtt
from hardware import detect_hardware

CONFIG = load_config()
STATIC_DIR = CONFIG.models_dir.parent / "static"

app = FastAPI(title="TranscribeNode", version="1.2.1")
manager = EngineManager(FasterWhisperEngine(), str(CONFIG.models_dir))

RESPONSE_FORMATS = {"json", "text", "srt", "vtt", "verbose_json"}


class LoadRequest(BaseModel):
    model: str | None = None


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/system")
async def system() -> dict[str, object]:
    hw = detect_hardware()
    return {
        "device": hw.device,
        "compute_type": hw.compute_type,
        "available_memory_gb": hw.available_memory_gb,
        "platform": hw.platform,
        "gpu_name": hw.gpu_name,
        "recommended_model": recommend_model(hw.available_memory_gb),
        "default_model": CONFIG.default_model,
    }


@app.get("/v1/models")
async def list_models() -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {
                "id": spec.name,
                "object": "model",
                "owned_by": "transcribenode",
                "vram_gb": spec.vram_gb,
                "quality": spec.quality,
                "use_case": spec.use_case,
            }
            for spec in MODEL_CATALOG
        ],
    }


@app.get("/engine/status")
async def engine_status() -> dict[str, object]:
    return manager.status()


@app.get("/engine/log")
async def engine_log() -> dict[str, object]:
    return {"entries": manager.log_entries()}


@app.post("/engine/load")
async def engine_load(request: LoadRequest) -> dict[str, object]:
    model = request.model or CONFIG.default_model
    hw = detect_hardware()
    try:
        return await run_in_threadpool(manager.load, model, hw.device, hw.compute_type)
    except Exception as exc:  # surface load failures to the operator
        raise HTTPException(status_code=500, detail=f"Failed to load model: {exc}") from exc


@app.post("/engine/unload")
async def engine_unload() -> dict[str, object]:
    return manager.unload()


async def _handle_transcription(
    task: str,
    file: UploadFile,
    model: str | None,
    language: str | None,
    prompt: str | None,
    response_format: str,
    temperature: float,
    timestamp_granularities: list[str] | None,
    vad_filter: bool,
    condition_on_previous_text: bool,
):
    if response_format not in RESPONSE_FORMATS:
        raise HTTPException(
            status_code=400, detail=f"Unsupported response_format: {response_format}"
        )
    if not manager.is_loaded:
        raise HTTPException(status_code=409, detail="No model loaded. Load a model first.")

    granularities = timestamp_granularities or ["segment"]
    options = TranscribeOptions(
        task=task,
        language=language,
        prompt=prompt,
        temperature=temperature,
        word_timestamps="word" in granularities,
        vad_filter=vad_filter,
        condition_on_previous_text=condition_on_previous_text,
    )

    suffix = Path(file.filename or "audio").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = await run_in_threadpool(
            manager.transcribe, tmp_path, file.filename or "audio", options
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if response_format == "text":
        return PlainTextResponse(result.text)
    if response_format == "srt":
        return PlainTextResponse(to_srt(result.segments))
    if response_format == "vtt":
        return PlainTextResponse(to_vtt(result.segments))
    if response_format == "verbose_json":
        return JSONResponse(to_verbose_json(result))
    return JSONResponse({"text": result.text})


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    model: str | None = Form(None),
    language: str | None = Form(None),
    prompt: str | None = Form(None),
    response_format: str = Form("json"),
    temperature: float = Form(0.0),
    timestamp_granularities: list[str] | None = Form(None),
    vad_filter: bool = Form(True),
    condition_on_previous_text: bool = Form(False),
):
    return await _handle_transcription(
        "transcribe",
        file,
        model,
        language,
        prompt,
        response_format,
        temperature,
        timestamp_granularities,
        vad_filter,
        condition_on_previous_text,
    )


@app.post("/v1/audio/translations")
async def translations(
    file: UploadFile = File(...),
    model: str | None = Form(None),
    prompt: str | None = Form(None),
    response_format: str = Form("json"),
    temperature: float = Form(0.0),
    timestamp_granularities: list[str] | None = Form(None),
    vad_filter: bool = Form(True),
    condition_on_previous_text: bool = Form(False),
):
    # Whisper's translate task only outputs English; no target-language parameter exists.
    return await _handle_transcription(
        "translate",
        file,
        model,
        None,
        prompt,
        response_format,
        temperature,
        timestamp_granularities,
        vad_filter,
        condition_on_previous_text,
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _open_browser_when_ready(url: str) -> None:
    """Open the UI in the default browser once the server is accepting connections."""
    import socket
    import threading
    import webbrowser

    def wait_and_open() -> None:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            with socket.socket() as sock:
                sock.settimeout(0.5)
                if sock.connect_ex(("127.0.0.1", CONFIG.port)) == 0:
                    break
            time.sleep(0.25)
        webbrowser.open(url)

    threading.Thread(target=wait_and_open, daemon=True).start()


if __name__ == "__main__":
    import uvicorn

    _open_browser_when_ready(f"http://localhost:{CONFIG.port}")
    uvicorn.run(app, host=CONFIG.host, port=CONFIG.port)
