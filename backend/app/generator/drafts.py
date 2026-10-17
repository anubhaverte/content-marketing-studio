"""Deterministic draft generator for ID Card Studio.

Selects and merges compatible layout and theme combinations from the catalog
based on Brief style hints and event metadata.
"""
from typing import Optional

from app.brief.schema import Brief
from app.generator.library import (
    get_layout,
    get_theme,
    list_layouts,
    list_themes,
)
from app.spec.loader import merge_design_spec
from app.spec.schema import DesignSpec, EventInfo, Layout, Theme

VARIANT_PRIMARY_COLORS = ["#D9480F", "#2F9E44", "#7950F2", "#E8590C", "#0C8599", "#1098AD"]


def score_combination(layout: Layout, theme: Theme, brief: Optional[Brief] = None) -> int:
    """Deterministic score for a layout + theme pair against brief style hints and event details."""
    score = 0
    if brief is None:
        return score

    # Collect all available text hints from brief
    search_texts = []
    if brief.style_hint:
        search_texts.append(brief.style_hint.lower())
    if brief.tagline:
        search_texts.append(brief.tagline.lower())
    if brief.event_name:
        search_texts.append(brief.event_name.lower())

    combined_text = " ".join(search_texts)
    if not combined_text:
        return score

    l_name = layout.name.lower()
    t_name = theme.name.lower()

    # Exact name matches
    if l_name in combined_text:
        score += 15
    if t_name in combined_text:
        score += 15

    # Layout matches:
    if any(k in combined_text for k in ("minimal", "clean", "simple", "modern", "subtle", "lightweight")):
        if l_name == "minimal":
            score += 12
        if t_name == "clean_light":
            score += 8

    if any(k in combined_text for k in ("split", "sidebar", "two-tone", "pillar", "asymmetric", "divider")):
        if l_name == "split":
            score += 15

    if any(k in combined_text for k in ("classic", "formal", "traditional", "academic", "conference", "standard")):
        if l_name == "classic":
            score += 12

    # Theme matches:
    if any(k in combined_text for k in ("dark", "tech", "techy", "cyber", "terminal", "night", "hack", "hackathon", "ai", "coding")):
        if t_name == "dark_tech":
            score += 15
        elif theme.colors.background.upper() not in ("#FFFFFF", "#FAFAFA", "#FFF7ED"):
            score += 5

    if any(k in combined_text for k in ("bold", "vibrant", "energetic", "fest", "celebration", "creative", "party")):
        if t_name == "bold_event":
            score += 15

    if any(k in combined_text for k in ("clean", "light", "white", "minimalist", "corporate")):
        if t_name == "clean_light":
            score += 12

    return score


def build_event_info_from_brief(brief: Optional[Brief] = None, event: Optional[EventInfo] = None) -> EventInfo:
    """Build EventInfo prioritizing explicitly provided event details, without inventing data."""
    if event is not None and (event.event_name or event.tagline or event.venue or event.dates):
        return event

    if brief is not None:
        return EventInfo(
            event_name=brief.event_name,
            tagline=brief.tagline,
            dates=brief.dates,
            venue=brief.venue,
        )

    return EventInfo()


def generate_drafts(
    brief: Optional[Brief] = None,
    event: Optional[EventInfo] = None,
    count: int = 3,
    layout_names: Optional[list[str]] = None,
    theme_names: Optional[list[str]] = None,
    allow_theme_variations: bool = False,
) -> tuple[list[DesignSpec], bool]:
    """Generate candidate DesignSpecs deterministically.

    Args:
        brief: Optional Brief specifying style hints and event details.
        event: Optional explicit EventInfo.
        count: Desired number of drafts (1 to 6).
        layout_names: Optional list of layout names (defaults to catalog).
        theme_names: Optional list of theme names (defaults to catalog).
        allow_theme_variations: If True and the catalog has fewer unique layout+theme
                                combinations than requested count, generates distinct
                                deterministic primary color variants marked as mock.

    Returns:
        tuple (drafts: list[DesignSpec], is_mock: bool)
    """
    avail_layouts = layout_names if layout_names is not None else list_layouts()
    avail_themes = theme_names if theme_names is not None else list_themes()

    if not avail_layouts or not avail_themes:
        return [], True

    # Build EventInfo
    event_info = build_event_info_from_brief(brief, event)

    # 1. Load available models safely
    loaded_layouts: dict[str, Layout] = {}
    for l_name in avail_layouts:
        try:
            loaded_layouts[l_name] = get_layout(l_name)
        except Exception:
            continue

    loaded_themes: dict[str, Theme] = {}
    for t_name in avail_themes:
        try:
            loaded_themes[t_name] = get_theme(t_name)
        except Exception:
            continue

    if not loaded_layouts or not loaded_themes:
        return [], True

    # 2. Form all unique pairs and score them
    pairs = []
    for l_name, l_obj in sorted(loaded_layouts.items()):
        for t_name, t_obj in sorted(loaded_themes.items()):
            score = score_combination(l_obj, t_obj, brief)
            pairs.append((score, l_name, t_name, l_obj, t_obj))

    # Deterministic sort: highest score first; tie break on layout_name, then theme_name
    pairs.sort(key=lambda item: (-item[0], item[1], item[2]))

    # 3. Pick candidates prioritizing diversity
    selected_pairs: list[tuple[str, str, Layout, Theme]] = []
    seen_layouts: set[str] = set()
    seen_themes: set[str] = set()

    # Pass 1: Try to pick pairs where both layout and theme are unused
    for _, l_name, t_name, l_obj, t_obj in pairs:
        if len(selected_pairs) >= count:
            break
        if l_name not in seen_layouts and t_name not in seen_themes:
            selected_pairs.append((l_name, t_name, l_obj, t_obj))
            seen_layouts.add(l_name)
            seen_themes.add(t_name)

    # Pass 2: Pick pairs where at least layout or theme is unused
    if len(selected_pairs) < count:
        for _, l_name, t_name, l_obj, t_obj in pairs:
            if len(selected_pairs) >= count:
                break
            if (l_name, t_name) not in [(p[0], p[1]) for p in selected_pairs]:
                if l_name not in seen_layouts or t_name not in seen_themes:
                    selected_pairs.append((l_name, t_name, l_obj, t_obj))
                    seen_layouts.add(l_name)
                    seen_themes.add(t_name)

    # Pass 3: Pick any remaining distinct catalog pairs
    if len(selected_pairs) < count:
        for _, l_name, t_name, l_obj, t_obj in pairs:
            if len(selected_pairs) >= count:
                break
            if (l_name, t_name) not in [(p[0], p[1]) for p in selected_pairs]:
                selected_pairs.append((l_name, t_name, l_obj, t_obj))

    # 4. Generate merged DesignSpecs
    drafts: list[DesignSpec] = []
    for l_name, t_name, l_obj, t_obj in selected_pairs:
        spec = merge_design_spec(layout=l_obj, theme=t_obj, event=event_info)
        drafts.append(spec)

    is_mock = False

    # 5. Fallback variation mode if requested and catalog is smaller than count
    if len(drafts) < count and allow_theme_variations and drafts:
        is_mock = True
        base_spec = drafts[0]
        needed = count - len(drafts)
        for i in range(needed):
            spec_copy = base_spec.model_copy(deep=True)
            color = VARIANT_PRIMARY_COLORS[i % len(VARIANT_PRIMARY_COLORS)]
            colors_data = spec_copy.theme.colors.model_dump()
            colors_data["primary"] = color
            spec_copy.theme = spec_copy.theme.model_copy(
                update={"colors": type(spec_copy.theme.colors)(**colors_data)}
            )
            drafts.append(spec_copy)

    return drafts, is_mock
