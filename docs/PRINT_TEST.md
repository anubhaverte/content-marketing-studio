# Print test

1. Generate `studio/sample_data/contact_sheet.png` with
   `python studio\design_tools\make_contact_sheet.py`, or use
   `studio/sample_data/preview_local.png` for one card.
2. Print with **Actual size**, **100%**, or **Scale: 100%**. Disable
   **Fit to page**, **Shrink oversized pages**, and automatic borderless expansion.
3. The canvas is 60 x 92 mm, including 3 mm bleed; card trim is 54 x 86 mm.
   Check the output dimensions with a ruler.
4. Cut at the trim boundary, not the outer canvas edge. Verify backgrounds
   extend into the bleed and that critical text, logos, photos, and QR codes
   remain within the safe area.
5. Inspect the 7 mm safe margin from the canvas edge and ensure trimming does
   not clip any important content.
6. Scan the QR code after cutting; the local stand-in's payload is
   `TEST-ID-<id>` (or `TEST-ID-MISSING-<row>` for an empty ID), not a live
   verification URL. Confirm its quiet zone remains intact.
7. Repeat in grayscale and verify badge shape, border pattern, and explicit
   role label are distinguishable.

The contact sheet is a QA preview, not a press-ready imposition: it has no
individual crop marks. Use a ruler to locate the 3 mm bleed inset when
evaluating a printed card.
