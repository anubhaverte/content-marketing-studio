# Shared assets

- `logos/`  ACM NIT Surat and SVNIT logos (SVG or very high-res PNG). The files here are PLACEHOLDERS. Replace them with the real logos using the same file names.
- `fonts/`  Font files (Poppins, Inter). Real fonts are set up in Phase 1.
- `art/`    Decorative SVG artwork exported from Figma, used by `svg_asset` elements.

## Logo files and formatting

Place the ACM NIT Surat logo here as `acm.svg` or `acm.png`, and the SVNIT logo as `svnit.svg` or `svnit.png`. SVG files must have a four-number `viewBox`. The renderer reads the PNG pixel dimensions or SVG viewBox, preserves the aspect ratio, and embeds each logo in the card SVG as a data URI. Missing files are shown as labelled placeholders.
