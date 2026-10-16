# Fonts

The themes use free fonts available from [Google Fonts](https://fonts.google.com/).
The font binaries are not included in this repository; download and place the
static TrueType files below in `studio/assets/fonts/` (the folder is currently
empty). The theme JSON paths are relative to the `studio/` directory.

| File to place in `studio/assets/fonts/` | Family / style | License |
| --- | --- | --- |
| `Inter-Regular.ttf` | [Inter](https://fonts.google.com/specimen/Inter) Regular | SIL Open Font License 1.1 |
| `Inter-Bold.ttf` | [Inter](https://fonts.google.com/specimen/Inter) Bold | SIL Open Font License 1.1 |
| `SpaceGrotesk-Bold.ttf` | [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk) Bold | SIL Open Font License 1.1 |

Inter and Space Grotesk are distributed under the SIL Open Font License 1.1.
Keep the upstream `OFL.txt` license and copyright notices with the font
distribution when redistributing the binaries. Download each family from its
Google Fonts page and select the listed static style; save it under the exact
filename shown above. Do not substitute a variable font unless the renderer
supports variable-font files and the theme paths are updated to match.

The logo folder is also intentionally empty. Import approved raster artwork
as `studio/assets/logos/acm_nit_surat.png` and
`studio/assets/logos/svnit.png`; the temporary preview fits these within the
layout boxes without stretching. Until supplied, it draws text stand-ins.

| Theme | Heading font | Body font |
| --- | --- | --- |
| `clean_light` | Inter Bold | Inter Regular |
| `dark_tech` | Space Grotesk Bold | Inter Regular |
| `bold_event` | Space Grotesk Bold | Inter Regular |
