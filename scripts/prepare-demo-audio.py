"""Generate stock English speech and word-aligned captions for the contest demo.

Run with the isolated media venv; does not access application credentials.
"""
import asyncio
import json
import re
import subprocess
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".tools/demo-recording-20261005"
OUT = ROOT / "outputs/contest-demo-en"
VOICE = "en-US-AndrewMultilingualNeural"


def duration(file):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file)
    ], text=True).strip())


def stamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


async def main():
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    paragraphs = re.split(r"\n\s*\n", (ROOT / "docs/contest-demo-narration-en.txt").read_text().strip())
    assert len(paragraphs) == 8
    cues, sections, start = [], [], 0.0
    for i, text in enumerate(paragraphs):
        audio = WORK / f"voice-{i + 1:02}.mp3"
        boundary_file = WORK / f"voice-{i + 1:02}-words.json"
        spoken = text.replace("DemoUSD", "demo U S D")
        if audio.exists() and boundary_file.exists():
            words = json.loads(boundary_file.read_text())
        else:
            words = []
            # Only public demonstration narration is sent to the speech service.
            communicator = edge_tts.Communicate(
                spoken, VOICE, rate="-7%", boundary="WordBoundary"
            )
            with audio.open("wb") as target:
                async for event in communicator.stream():
                    if event["type"] == "audio":
                        target.write(event["data"])
                    elif event["type"] == "WordBoundary":
                        words.append(event)
            assert words and audio.stat().st_size > 0
            boundary_file.write_text(json.dumps(words, indent=2))
        spoken_duration = duration(audio)
        section_length = spoken_duration + 1.5
        # Preserve source punctuation omitted by the service's word events.
        cursor = 0
        display_words = []
        for word in words:
            match = re.search(r"(?<!\w)" + re.escape(word["text"]) + r"(?!\w)",
                              spoken[cursor:], re.IGNORECASE)
            assert match, f"Unaligned caption word: {word['text']}"
            end = cursor + match.end()
            punctuation = re.match(r"[^\w\s]*", spoken[end:]).group()
            display_words.append({**word, "text": spoken[cursor + match.start():end] + punctuation})
            cursor = end + len(punctuation)
        joined_words = []
        index = 0
        while index < len(display_words):
            group = display_words[index:index + 4]
            if len(group) == 4 and [re.sub(r"[^a-z]", "", w["text"].lower()) for w in group] == ["demo", "u", "s", "d"]:
                last = group[-1]
                suffix = re.sub(r"^[dD]", "", last["text"])
                joined_words.append({**group[0], "text": "DemoUSD" + suffix,
                                     "duration": last["offset"] + last["duration"] - group[0]["offset"]})
                index += 4
            else:
                joined_words.append(display_words[index])
                index += 1
        # A 0.5-second visual lead-in precedes each paragraph.
        group = []
        for word in joined_words:
            group.append(word)
            joined = " ".join(w["text"] for w in group).replace('“', '').replace('”', '')
            if len(joined) >= 105 or re.search(r"[.!?][\u201d\"]?$", word["text"]):
                cues.append({
                    "start": start + 0.5 + group[0]["offset"] / 10000000,
                    "end": start + 0.5 + (word["offset"] + word["duration"]) / 10000000,
                    "text": joined.replace("demo U S D", "DemoUSD"),
                })
                group = []
        if group:
            last = group[-1]
            cues.append({
                "start": start + 0.5 + group[0]["offset"] / 10000000,
                "end": start + 0.5 + (last["offset"] + last["duration"]) / 10000000,
                "text": " ".join(w["text"] for w in group).replace("demo U S D", "DemoUSD").replace('“', '').replace('”', ''),
            })
        padded = WORK / f"voice-{i + 1:02}.wav"
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(audio),
            "-af", "adelay=500:all=1,apad", "-t", str(section_length),
            "-ar", "48000", "-ac", "1", str(padded)
        ], check=True)
        sections.append({"number": i + 1, "start": start, "duration": section_length,
                         "spoken_duration": spoken_duration, "audio": str(padded)})
        start += section_length
        print(f"Section {i + 1}: speech {spoken_duration:.2f}s / timeline {section_length:.2f}s", flush=True)
    assert start <= 180, f"Audio timeline too long: {start:.2f}s"
    timeline = {"voice": VOICE, "rate": "-7%", "duration": start,
                "sections": sections, "cues": cues}
    (WORK / "audio-timeline.json").write_text(json.dumps(timeline, indent=2))
    srt = "\n\n".join(f"{i + 1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}"
                       for i, c in enumerate(cues)) + "\n"
    (OUT / "openworkproof-settlement-demo-en.srt").write_text(srt)
    concat = WORK / "audio-concat.txt"
    concat.write_text("\n".join(f"file '{s['audio']}'" for s in sections) + "\n")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", str(concat), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000",
        "-c:a", "pcm_s16le", str(WORK / "narration.wav")
    ], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(WORK / "narration.wav"),
        "-c:a", "libmp3lame", "-b:a", "192k", str(OUT / "narration-en.mp3")
    ], check=True)
    print(f"Prepared {start:.2f}s, {len(cues)} aligned cues; stock voice, no voice cloning.")


if __name__ == "__main__":
    asyncio.run(main())
