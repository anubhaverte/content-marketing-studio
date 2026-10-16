"""The toolchain produces the right physical sizes."""
import xml.etree.ElementTree as ET

from PIL import Image
from pypdf import PdfReader

import hello_card  # from backend/scripts

PDF_W_PT, PDF_H_PT = 170.08, 260.79   # 60 x 92 mm in points
PNG_W_PX, PNG_H_PX = 709, 1087        # 60 x 92 mm at 300 DPI


def test_hello_card_sizes(tmp_path):
    files = hello_card.run(tmp_path)

    box = PdfReader(str(files["pdf"])).pages[0].mediabox
    assert abs(float(box.width) - PDF_W_PT) <= 0.5
    assert abs(float(box.height) - PDF_H_PT) <= 0.5

    width, height = Image.open(files["png"]).size
    assert abs(width - PNG_W_PX) <= 2
    assert abs(height - PNG_H_PX) <= 2

    assert files["svg"].read_text(encoding="utf-8").startswith("<?xml")


def test_hello_card_is_deterministic():
    person = {"name": "Priya Venkatakrishnan", "role": "participant"}
    a = hello_card.render_hello_svg(person, debug_guides=True)
    b = hello_card.render_hello_svg(person, debug_guides=True)
    assert a == b


def test_hello_card_embeds_logos_and_real_font_files():
    svg = hello_card.render_hello_svg({"name": "Priya Venkatakrishnan", "role": "participant"})

    ET.fromstring(svg)
    assert svg.count("data:image/svg+xml;base64,") == 2
    assert svg.count("data:font/ttf;base64,") == 2
    assert 'preserveAspectRatio="xMidYMid meet"' in svg
    assert "<text" in svg
