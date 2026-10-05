"""Extract source or output frames for manual visual verification."""
import io
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

source, output, *times = sys.argv[1:]
times = [float(t) for t in times]
sheet = Image.new('RGB', (960, ((len(times) + 1) // 2) * 294), '#10222d')
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
for i, time in enumerate(times):
    data = subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', str(time), '-i', source,
        '-frames:v', '1', '-vf', 'scale=480:270', '-f', 'image2pipe', '-vcodec', 'png', '-'])
    frame = Image.open(io.BytesIO(data))
    x, y = i % 2 * 480, i // 2 * 294
    sheet.paste(frame, (x, y))
    ImageDraw.Draw(sheet).text((x + 12, y + 270), f'{time:.2f}s', font=font, fill='white')
Path(output).parent.mkdir(parents=True, exist_ok=True)
sheet.save(output)
