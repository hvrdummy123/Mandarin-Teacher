# duihua · portfolio media

Product demos of **duihua 对话** — a personal Mandarin speaking coach (voice + rich transcript).

Generated with Playwright against the live local app. Re-record anytime:

```bash
make dev        # in one terminal
make portfolio  # or: node scripts/portfolio/record.mjs
# optional single clip: PORTFOLIO_ONLY=04-review-before-send make portfolio
```

## Clips

| File | What it shows |
|------|----------------|
| `01-conversation.mp4` / `.gif` | Stacked pinyin · hanzi · English, word tap → dictionary, save word |
| `02-topics.mp4` / `.gif` | Browse scenarios and start a topic role-play |
| `03-tour.mp4` / `.gif` | Chat · Topics · Saved words · Progress + theme toggle |
| `04-review-before-send.mp4` / `.gif` | Review transcript before send, with topic-aware STT repair |
| `05-mobile.mp4` / `.gif` | Same product on a phone-sized viewport |

Stills: `still-chat.png`, `still-topics.png`, `still-progress.png`, plus a mid-clip `.png` poster per video.

## Portfolio tips

- Prefer **MP4** for project pages / case studies (sharper, smaller).
- Prefer **GIF** for README embeds and quick LinkedIn/Twitter previews.
- Suggested caption: *“Speak Mandarin with live pinyin, hanzi, and English — plus topic role-play and review-before-send.”*
