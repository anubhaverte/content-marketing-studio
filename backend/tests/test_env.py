"""The environment has what the project needs."""
import importlib

import pytest

PACKAGES = ["fastapi", "uvicorn", "pydantic", "jinja2", "cairosvg", "PIL", "pandas", "segno",
            "cv2", "multipart", "pypdf", "reportlab", "dotenv", "httpx"]


@pytest.mark.parametrize("pkg", PACKAGES)
def test_package_imports(pkg):
    importlib.import_module(pkg)


def test_cairosvg_renders_tiny_svg():
    import cairosvg

    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm"><rect width="10" height="10"/></svg>'
    assert cairosvg.svg2png(bytestring=svg.encode())[:4] == b"\x89PNG"
