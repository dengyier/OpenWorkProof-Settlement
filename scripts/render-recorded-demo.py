"""Edit the actual Devnet recording; never generates or replaces application UI."""
import json
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.tools/demo-recording-20261005'
OUT = ROOT / 'outputs/contest-demo-en'
RAW = WORK / 'two-paths-raw.mkv'
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
timeline = json.loads((WORK / 'audio-timeline.json').read_text())

# Source seconds were inspected against extracted frames before choosing cuts.
# Final chunks hold the last recorded frame when narration requires extra time.
scenes = [
    ('Reviewable work. Explicit payment.', 'ORDER A / LIVE DEEPSEEK',
     ['A bounded code fix.', 'A signed delivery record.', 'A separate customer decision.', 'Solana Devnet only.'],
     [(40, 4, 20.196, 'app')]),
    ('Freeze terms. Fund escrow.', 'ORDER A / LIVE DEEPSEEK',
     ['Source revision + permitted file', 'Immutable tests + parties + budget', 'Customer deposits 1 DemoUSD.'],
     [(40, 5, 5, 'app'), (50, 5, 5, 'wallet'), (148, 5, 6.476, 'app')]),
    ('Execute. Verify. Inspect.', 'ORDER A / LIVE DEEPSEEK',
     ['DeepSeek proposes the patch.', 'OWP protects read and patch.', 'Docker checks frozen tests.', 'Evidence is inspectable.'],
     [(159, 5, 5, 'app'), (180, 7, 7, 'app'), (190, 8, 10.356, 'app')]),
    ('Acceptance is not payment.', 'ORDER A / CUSTOMER SIGNATURE',
     ['Customer reviews the work.', 'Phantom signs acceptance.', 'Tokens stay in escrow until a separate release.'],
     [(208, 5, 6, 'wallet'), (255, 6, 7.428, 'app')]),
    ('Approve release. Confirm finality.', 'ORDER A / SETTLED',
     ['A second wallet approval.', 'Designated attester co-signs.', 'Verified RPC result:', '+1 DemoUSD to provider', 'Vault balance: 0'],
     [(278, 5, 6, 'wallet'), (374, 10, 11.748, 'app')]),
    ('Tests passed. Customer rejected.', 'ORDER B / REFERENCE PATCH, NO LLM',
     ['A separate order, not Order A.', 'Verification remains VERIFIED.', 'Customer signs rejection.', 'Disputed: release blocked.', 'Rejection is not automatic refund.'],
     [(758, 3, 3, 'app'), (771, 4, 5, 'wallet'), (797, 3, 3, 'app'),
      (818, 3, 3, 'wallet'), (857, 5, 8.068, 'app')]),
    ('Consent. Co-sign. Refund.', 'ORDER B / REFUNDED',
     ['Provider consents to cancellation.', 'Customer co-signs the refund.', 'Verified RPC result:', '+1 DemoUSD to customer', 'Provider delta: 0 / Vault: 0',
      'Repeat refund/release refused.*', '*Read-only state simulation; not broadcast.'],
     [(880, 7, 8, 'wallet'), (905, 10, 16.252, 'app')]),
    ('Clear trust boundaries.', 'DEVNET PROTOTYPE / NOT REAL MONEY',
     ['Chain: permissions and transfers.', 'App attester: evidence checks.', 'Provider + attester are app-owned.', 'Program is upgradeable.', 'No automatic arbitration.', 'OWP Core predates this entry.', 'This entry adds settlement.'],
     [(905, 10, 31.404, 'app')]),
]


def run(args):
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', *map(str, args)], check=True)


def wrapped(draw, text, xy, width, size, bold=False, color='white', gap=8):
    font = ImageFont.truetype(BOLD if bold else FONT, size)
    words, line, lines = text.split(), '', []
    for word in words:
        candidate = (line + ' ' + word).strip()
        if draw.textlength(candidate, font=font) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += size + gap
    return y


def card(index, title, label, bullets):
    image = Image.new('RGB', (1920, 1080), '#0a1d27')
    draw = ImageDraw.Draw(image)
    draw.line((40, 96, 1880, 96), fill='#31505e', width=2)
    draw.text((44, 30), 'OPENWORKPROOF / SETTLEMENT', font=ImageFont.truetype(BOLD, 30), fill='#e9f1f2')
    draw.text((1450, 35), 'DEVNET / TEST TOKENS', font=ImageFont.truetype(FONT, 25), fill='#88c8be')
    draw.text((48, 135), f'{index:02d} / 08', font=ImageFont.truetype(FONT, 26), fill='#88c8be')
    y = wrapped(draw, title, (48, 193), 510, 48, bold=True) + 30
    y = wrapped(draw, label, (48, y), 510, 22, color='#88c8be') + 26
    for text in bullets:
        size = 20 if text.startswith('*') else 28
        y = wrapped(draw, text, (48, y), 505, size, color='#d8e3e6', gap=7) + 17
    assert y < 925, f'Card {index} exceeds available space: {y}'
    id_label = '2f88f90a80f2' if index <= 5 else '4425870c5020'
    draw.text((650, 903), f'Order {id_label}… / actual capture / cropped / waits cut / frames held',
              font=ImageFont.truetype(FONT, 18), fill='#92afb8')
    draw.rectangle((30, 928, 1890, 1055), fill='#06131b')
    file = WORK / f'card-{index:02}.png'
    image.save(file)
    return file


def main():
    clips, edit = [], []
    for index, (title, label, bullets, shots) in enumerate(scenes, 1):
        section = timeline['sections'][index - 1]
        assert abs(sum(shot[2] for shot in shots) - section['duration']) < .002
        background = card(index, title, label, bullets)
        for j, (start, captured, duration, layout) in enumerate(shots):
            output = WORK / f'edit-{index:02}-{j:02}.mp4'
            # Wallet crop omits Chrome's translation bubble at the far right.
            transform = ('crop=1600:1080:0:0,scale=1156:780,pad=1280:780:62:0:color=0x0c2029' if layout == 'wallet'
                         else 'crop=980:750:680:120,scale=1019:780,pad=1280:780:130:0:color=0x0c2029')
            filt = f'[0:v]{transform},fps=30,tpad=stop_mode=clone:stop_duration={duration}[screen];[1:v][screen]overlay=608:112:shortest=1,format=yuv420p[out]'
            run(['-ss', start, '-t', captured, '-i', RAW, '-loop', '1', '-i', background,
                 '-filter_complex', filt, '-map', '[out]', '-t', duration, '-an',
                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-r', '30', output])
            clips.append(output)
            edit.append({'scene': index, 'source_start': start, 'source_duration': captured,
                         'edited_duration': duration, 'layout': layout, 'last_frame_held': duration > captured})
        print(f'Rendered scene {index}/8', flush=True)
    concat = WORK / 'edit-concat.txt'
    concat.write_text('\n'.join(f"file '{clip}'" for clip in clips) + '\n')
    run(['-f', 'concat', '-safe', '0', '-i', concat, '-c', 'copy', WORK / 'picture.mp4'])

    caption_entries, cursor = [], 0.0
    for index, cue in enumerate(timeline['cues']):
        assert cursor <= cue['start'] < cue['end'] <= timeline['duration']
        if cue['start'] > cursor:
            caption_entries.append(('blank.png', cue['start'] - cursor))
        im = Image.new('RGBA', (1920, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype(FONT, 36)
        lines = textwrap.wrap(cue['text'], width=78)
        assert len(lines) <= 2
        for j, line in enumerate(lines):
            w = draw.textlength(line, font=font)
            assert w <= 1760
            draw.text(((1920 - w) / 2, 17 + j * 45), line, font=font, fill='white')
        name = f'caption-{index:02}.png'
        im.save(WORK / name)
        caption_entries.append((name, cue['end'] - cue['start']))
        cursor = cue['end']
    Image.new('RGBA', (1920, 128), (0, 0, 0, 0)).save(WORK / 'blank.png')
    caption_entries.append(('blank.png', timeline['duration'] - cursor))
    captions = WORK / 'caption-concat.txt'
    captions.write_text('\n'.join(f"file '{WORK / name}'\noption framerate 1000\nduration {length:.6f}" for name, length in caption_entries)
                        + f"\nfile '{WORK / 'blank.png'}'\noption framerate 1000\n")
    run(['-f', 'concat', '-safe', '0', '-i', captions, '-vf', 'fps=30', '-t', timeline['duration'],
         '-c:v', 'qtrle', '-pix_fmt', 'argb', WORK / 'captions.mov'])
    final = OUT / 'openworkproof-settlement-demo-en.mp4'
    run(['-i', WORK / 'picture.mp4', '-i', WORK / 'captions.mov', '-i', WORK / 'narration.wav',
         '-i', OUT / 'openworkproof-settlement-demo-en.srt', '-filter_complex',
         '[0:v][1:v]overlay=0:928:eof_action=pass:shortest=0,format=yuv420p[out]', '-map', '[out]', '-map', '2:a', '-map', '3:s',
         '-t', timeline['duration'], '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-r', '30',
         '-c:a', 'aac', '-b:a', '192k', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=eng',
         '-metadata:s:a:0', 'language=eng', '-movflags', '+faststart', final])
    (OUT / 'edit-decision-list.json').write_text(json.dumps({'raw_recording': str(RAW),
        'duration': timeline['duration'], 'scenes': edit, 'narration': timeline['voice'],
        'caption_method': 'word-boundary aligned, burned in and optional English subtitle stream'}, indent=2) + '\n')
    print(f'Final MP4: {final}', flush=True)


if __name__ == '__main__':
    main()
