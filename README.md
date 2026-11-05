# The Wildheart — Blender animation

A procedural cinematic 3D scene of an ancient living-wood staff crowned by a prismatic magical orb.

## Final render target
- MP4: 1920×1080, 60 fps, 8 seconds, H.264
- Editable source: `wildheart_staff.blend`
- Visual proof: contact sheet + 4-second preview still

## Scene features
- Procedural walnut-like wood grain and root-shaped branches
- Animated 4D-noise emissive orb with blue, cyan, violet, magenta and amber color currents
- Rotating gold, cyan and violet orbital rings
- Aether spirals around the shaft
- Floating spirit motes and grove silhouettes
- Cinematic lighting, depth of field and fog-glow compositing

## Build
GitHub Actions downloads and checksum-verifies Blender 4.5.15 LTS, renders the 480-frame sequence, encodes H.264 MP4 at 60 fps, validates the output with ffprobe, and publishes the MP4 and editable .blend file as a GitHub Release.

No external assets are required.
