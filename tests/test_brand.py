"""The integration's brand images: Home Assistant finds them, and they have
the names and sizes its brand rules ask."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_custom_components
from PIL import Image

BRAND = Path(__file__).parent.parent / "custom_components" / "massimo" / "brand"


async def test_home_assistant_finds_the_brand_images(hass: HomeAssistant) -> None:
    """The loader says the integration carries brand images."""
    integration = (await async_get_custom_components(hass))["massimo"]
    assert integration.has_branding


def test_the_brand_images_are_as_home_assistant_asks() -> None:
    """Icons square at 256 and 512 px, logos 128 and 256 px high, each with
    its dark one, transparent and trimmed: something drawn on every edge of a
    logo, and on both sides of an icon (the mark is wider than tall)."""
    for prefix in ("", "dark_"):
        for name, size in ((f"{prefix}icon.png", 256), (f"{prefix}icon@2x.png", 512)):
            with Image.open(BRAND / name) as im:
                assert im.size == (size, size), name
                assert im.mode == "RGBA", name
                left, top, right, bottom = im.getchannel("A").getbbox()
                assert (left, right) == (0, size), f"{name} is trimmed at the sides"
                assert top > 0 and bottom < size, f"{name} has transparent room above and below"
        for name, height in ((f"{prefix}logo.png", 128), (f"{prefix}logo@2x.png", 256)):
            with Image.open(BRAND / name) as im:
                assert im.height == height and im.width > height, name
                assert im.mode == "RGBA", name
                assert im.getchannel("A").getbbox() == (0, 0, im.width, height), f"{name} is trimmed"
    assert sorted(p.name for p in BRAND.iterdir()) == sorted(
        f"{prefix}{n}.png" for prefix in ("", "dark_") for n in ("icon", "icon@2x", "logo", "logo@2x")
    )
