---
name: yt-to-ren
version: 1.0.0
description: Extract YouTube video transcripts and inject them as market context into a trading AI (Ren/loop-bot). Supports metadata tagging, library management, and keyword search.
tags: [youtube, transcripts, trading, market-context, pipeline]
author: arc
platforms: [agent-zero, claude-code]
---

# YouTube to Ren Pipeline

Extract YouTube transcripts and push structured JSON data into a trading AI context library.

## Use When
- You want to feed market analysis videos to a trading bot
- Building a video-based knowledge library for an AI agent
- Extracting transcript data for research or summarization

## Dependencies
```bash
pip install youtube-transcript-api
```

## Core Script

Save as `yt_to_ren.py`:

```python
import json, os, sys
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi, FetchedTranscript

LIBRARY_DIR = "/app/data/video_library"  # adjust to your path
os.makedirs(LIBRARY_DIR, exist_ok=True)

def extract_video_id(url_or_id: str) -> str:
    if "youtube.com/watch?v=" in url_or_id:
        return url_or_id.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url_or_id:
        return url_or_id.split("youtu.be/")[1].split("?")[0]
    return url_or_id.strip()

def fetch_transcript(video_id: str) -> str:
    fetched: FetchedTranscript = YouTubeTranscriptApi.fetch(video_id)
    return " ".join(s.text for s in fetched)

def process_video(url: str, tags: list = None) -> dict:
    video_id = extract_video_id(url)
    transcript = fetch_transcript(video_id)
    entry = {
        "video_id": video_id,
        "url": f"https://youtube.com/watch?v={video_id}",
        "transcript": transcript[:50000],  # cap at 50k chars
        "tags": tags or [],
        "processed_at": datetime.utcnow().isoformat()
    }
    out_path = os.path.join(LIBRARY_DIR, f"{video_id}.json")
    with open(out_path, "w") as f:
        json.dump(entry, f, indent=2)
    print(f"Saved: {out_path} ({len(transcript)} chars)")
    return entry

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else input("YouTube URL: ")
    tags = sys.argv[2].split(",") if len(sys.argv) > 2 else []
    process_video(url, tags)
```

## Usage
```bash
# Process a single video
python yt_to_ren.py "https://youtube.com/watch?v=VIDEO_ID" "market-analysis,bitcoin"

# List library
ls /app/data/video_library/

# Search by keyword
grep -l "bitcoin" /app/data/video_library/*.json
```

## Integration with Ren Hub

If using the ren-hub FastAPI service, add a `/videos` router:
```python
# GET /videos — list all
# GET /videos/{video_id} — get transcript
# GET /videos/search?q=keyword — search
```

## Notes
- Transcripts capped at 50,000 chars to prevent context overflow
- Library limited to 100 videos (rotate oldest when full)
- Sanitize transcript text to prevent prompt injection
