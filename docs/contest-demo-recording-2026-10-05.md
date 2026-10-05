# English product demo — actual recording and verification

Recorded October 5, 2026, Asia/Shanghai. This is the product demonstration, not the separate founder/business presentation.

## Deliverables

- [MP4, English narration and captions](../outputs/contest-demo-en/openworkproof-settlement-demo-en.mp4)
- [English SRT](../outputs/contest-demo-en/openworkproof-settlement-demo-en.srt)
- English narration MP3 (local production sidecar; excluded from the code-review repository)
- [Public recorded-case evidence and Devnet Explorer links](../outputs/contest-demo-en/recorded-demo-evidence.json)
- Source cuts and held-frame durations (local edit-decision list; excluded from the code-review repository)

The final MP4 was uploaded to the user-approved YouTube channel `wudangyueqi` on October 5, 2026 as **unlisted**: https://youtu.be/iY_NE8bBbyI. YouTube reported no copyright issues; the signed-in watch page played successfully. An incognito watch page showed the correct title, description and Unlisted label, but playback required sign-in for YouTube's anti-bot check, so anonymous playback was not verified. English stock neural narration is disclosed in the description and platform AI setting.

The demo URL was saved in the Colosseum project draft. This is **not final submission**. The authenticated portal says final submission opens October 6 at 4:00 AM PDT (October 6, 2026, 19:00 Asia/Shanghai). A separate pitch video of up to two minutes, project graphic, new-code repository and founder submission profile remain required; see [submission progress](contest-submission-progress-2026-10-05.md).

## What the recording actually shows

The uncut source is a 969.10-second capture of the actual Chrome application and Phantom wallet on the project monitor. It remains locally under `.tools/demo-recording-20261005/two-paths-raw.mkv`, outside the public package. All customer wallet approvals were performed by the user. No wallet seed, password or API key was displayed.

The edited video uses cropped actual screen footage, cuts idle confirmation/finality waiting, and holds the last captured frame where needed for narration. This editing is labelled throughout. It does not synthesize application state or replay a fake wallet interaction. Editorial captions and verified-RPC summary cards are distinct from the application UI.

| Recorded case | Execution | Native customer decision | Finalized chain result |
| --- | --- | --- | --- |
| A — `2f88f90a80f237505ac44991c38c590c` | Live DeepSeek `deepseek-flash`; protected patch; immutable Docker tests | ACCEPTED | Settled; provider token account 4 → 5 DemoUSD; vault 1 → 0 |
| B — `4425870c502015b0714410c9a5a6e761` | Clearly labelled reference patch, no LLM call; verification passed | REJECTED | Disputed, then mutually Refunded; customer token account 1 → 2 DemoUSD; vault 1 → 0; provider remains 5 |

Amounts above are **test-token balances**, not dollars or USDC. Each terminal transfer is exactly 1 DemoUSD (1,000,000 raw units at six decimals), not the recipient's entire cumulative balance. Network fees and account rent are not returned by the refund.

## Fresh checks

`node scripts/verify-recorded-demo.cjs` verifies the Devnet genesis, native summary, frozen onchain terms, delivery commitments, final order state, empty vaults, pending-null state, successful finalized transaction statuses and terminal token deltas. The final recording's evidence is exported without private keys or model request/response bodies.

The deployed program refuses a repeated refund and release after refund with `InvalidState` / custom error 6003. These are read-only simulations with `sigVerify=false`, not broadcast failed transactions or proof of signer validity. The terminal refund itself was a real wallet-signed, finalized transaction.

## Media verification

- Final measured container/video: 167.933333 seconds (2:48); audio: 167.928 seconds, below the 180-second product-demo limit. Video/audio end times differ by less than one frame.
- H.264 / yuv420p, 1920 × 1080, 30 fps; AAC, 48 kHz, mono; MP4 fast-start.
- English captions burned into a dedicated dark lower band; optional `mov_text` English subtitle stream and SRT sidecar. Some players may show duplicate captions if the optional track is also enabled.
- Stock `en-US-AndrewMultilingualNeural` voice at -7% rate. No voice cloning or claim that a human recorded the narration. Perceived naturalness remains subject to user review.
- 32 caption cues use speech-service word-boundary timestamps. All cues were checked for valid, nonoverlapping times within narration duration. Full-file decoding completed without errors; sampled frames, including the final 167.7-second frame, were inspected. Encoding success alone is not subjective voice approval.

The source audio helper normalizes narration to a -16 LUFS target with -1.5 dB true-peak target. The encoded AAC check measured mean volume -16.9 dBFS and sample peak -1.4 dBFS (no full-scale sample clipping); these are not a separate measured LUFS/true-peak certification.

Final file: 7,158,317 bytes. SHA-256: `297c6a4f1cacb5bc32ff6fdcc9e120f84e4becee18e3774a6c91efa790b17a5a`.

## Trust boundaries retained in the video

The chain enforces permissions and transfers. The application attester checks offchain evidence. Provider and attester are application-owned test roles; the program is upgradeable. There is no independent arbitration, audit certification, real-money payment or customer-revenue claim. OWP Core predates this competition; this entry adds settlement integration. Verification, customer acceptance and settlement remain separate events.

## Reproduction

Run the media helpers using the isolated `.tools/media-venv` with `edge-tts==7.2.8` and `Pillow==12.1.1`, plus the local ffmpeg/ffprobe. They do not change application dependencies. Speech cache avoids repeated TTS calls; only the public narration is sent to the speech service.

```sh
.tools/media-venv/bin/python scripts/prepare-demo-audio.py
.tools/media-venv/bin/python scripts/render-recorded-demo.py
ffprobe -v error -show_format -show_streams outputs/contest-demo-en/openworkproof-settlement-demo-en.mp4
ffmpeg -v error -i outputs/contest-demo-en/openworkproof-settlement-demo-en.mp4 -f null -
```

Rendering requires the original local recording. The source-cut list is specific to that recording, not a generic automation of future wallet approvals.
