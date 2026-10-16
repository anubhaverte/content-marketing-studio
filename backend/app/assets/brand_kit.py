"""Load brand kits (logos, colors, fonts). ACM NIT Surat and SVNIT are built in."""
from app.spec.schema import BrandKit


def load_brand_kit(name: str = "default") -> BrandKit:
    """Return the brand kit with both logos as repo-relative paths.

    Raises:
        ValueError: If name is anything other than 'default'.
    """
    if name != "default":
        raise ValueError(f"Unknown brand kit '{name}'. Only 'default' is supported.")
    return BrandKit(
        logos={
            "acm_nitsurat": "assets/logos/acm_nitsurat.svg",
            "svnit": "assets/logos/svnit.svg",
        }
    )
