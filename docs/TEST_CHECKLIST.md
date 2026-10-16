# Design test checklist

Check each item on a rendered preview and on the printed test card where noted.

- [ ] Render the normal sample person in each layout.
- [ ] Render a name at least 45 characters long; verify it wraps or shrinks without clipping.
- [ ] Render a person with no photo; verify the placeholder appears and generation completes.
- [ ] Render participant, organizer, and mentor badges; verify the correct label and style for each.
- [ ] Leave `team` and `id` empty; verify their rows collapse and later content remains readable.
- [ ] Run `python studio\design_tools\check_contrast.py`; verify every listed pair meets the configured contrast minimum.
- [ ] Run `python studio\design_tools\validate_layouts.py`; verify important elements are inside the safe area.
- [ ] Print or view in grayscale; verify role shapes, borders, and labels remain distinct.
- [ ] Check that institutional logos use contain proportions and are not stretched. Current temporary preview uses text stand-ins until logo files are supplied.
- [ ] Scan a printed sample QR code with a phone; its temporary payload is `TEST-ID-<id>` (not a real verification URL).
- [ ] Print at 100% scale, cut along trim marks, and inspect bleed and safe margins using [PRINT_TEST.md](./PRINT_TEST.md).
