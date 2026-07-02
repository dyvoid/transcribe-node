"""Render a TranscriptionResult into the OpenAI response_format variants."""

from engine import Segment, TranscriptionResult


def format_timestamp(seconds: float, separator: str) -> str:
    total_ms = round(seconds * 1000)
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, millis = divmod(total_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def to_verbose_json(result: TranscriptionResult) -> dict[str, object]:
    segments = []
    for seg in result.segments:
        entry: dict[str, object] = {
            "id": seg.id,
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
        }
        if seg.words is not None:
            entry["words"] = [
                {"word": w.word, "start": w.start, "end": w.end} for w in seg.words
            ]
        segments.append(entry)

    return {
        "task": result.task,
        "language": result.language,
        "duration": result.duration,
        "text": result.text,
        "segments": segments,
    }


def to_srt(segments: list[Segment]) -> str:
    blocks = []
    for i, seg in enumerate(segments, start=1):
        start = format_timestamp(seg.start, ",")
        end = format_timestamp(seg.end, ",")
        blocks.append(f"{i}\n{start} --> {end}\n{seg.text.strip()}\n")
    return "\n".join(blocks)


def to_vtt(segments: list[Segment]) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = format_timestamp(seg.start, ".")
        end = format_timestamp(seg.end, ".")
        lines.append(f"{start} --> {end}")
        lines.append(seg.text.strip())
        lines.append("")
    return "\n".join(lines)
