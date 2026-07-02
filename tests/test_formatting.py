from engine import Segment, TranscriptionResult, Word
from formatting import format_timestamp, to_srt, to_verbose_json, to_vtt


def _segments():
    return [
        Segment(0, 0.0, 3.2, "Hello and welcome", [Word("Hello", 0.0, 0.4)]),
        Segment(1, 3.2, 5.0, "to the show", None),
    ]


def test_format_timestamp_srt_and_vtt_separators():
    assert format_timestamp(3661.5, ",") == "01:01:01,500"
    assert format_timestamp(3661.5, ".") == "01:01:01.500"


def test_to_srt_numbers_and_arrows():
    srt = to_srt(_segments())
    assert srt.startswith("1\n00:00:00,000 --> 00:00:03,200\nHello and welcome")
    assert "2\n00:00:03,200 --> 00:00:05,000\nto the show" in srt


def test_to_vtt_has_header():
    vtt = to_vtt(_segments())
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:03.200" in vtt


def test_verbose_json_includes_words_only_when_present():
    result = TranscriptionResult(
        "transcribe", "en", 5.0, "Hello and welcome to the show", _segments()
    )
    payload = to_verbose_json(result)
    assert payload["language"] == "en"
    assert "words" in payload["segments"][0]
    assert "words" not in payload["segments"][1]
