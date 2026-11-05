# The Wildheart — Blender animation

A procedural, asset-free cinematic scene of an ancient living-wood staff crowned by a prismatic, iridescent magic orb.

## Output
- `wildheart_staff.mp4`: 1280×720, 24 fps, 8 seconds, H.264
- `wildheart_staff.blend`: editable Blender scene
- `preview.png`: representative frame

## Render
GitHub Actions downloads the official Blender 4.5.15 Linux build, creates the scene with `render_magic_staff.py`, renders a PNG sequence, and encodes it to MP4 with FFmpeg.

The workflow runs after its first commit to the default branch, and can also be run manually from **Actions → Render The Wildheart**.

No external assets are required.
