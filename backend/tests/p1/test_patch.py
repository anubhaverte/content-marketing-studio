"""Tests for the patch engine (apply_patch)."""
import copy
import pytest

from app.generator.library import get_layout, get_theme
from app.refine.patch import apply_patch, PatchError
from app.spec.loader import merge_design_spec
from app.spec.schema import DesignSpec, PatchOp


@pytest.fixture
def base_spec() -> DesignSpec:
    """Fixture providing a merged classic + clean_light DesignSpec with element IDs."""
    layout = get_layout("classic")
    theme = get_theme("clean_light")
    return merge_design_spec(layout, theme)


def test_patch_set_by_index(base_spec: DesignSpec):
    """Set a field on an element using its numeric index."""
    op = PatchOp(op="set", path="elements.0.x", value=12.5)
    patched = apply_patch(base_spec, [op])

    assert patched.elements[0].x == 12.5
    assert base_spec.elements[0].x != 12.5


def test_patch_set_by_element_id(base_spec: DesignSpec):
    """Set a field on an element using its string element id."""
    # First assign an id to element 0
    setup_op = PatchOp(op="set", path="elements.0.id", value="accent_bar")
    spec_with_id = apply_patch(base_spec, [setup_op])

    edit_op = PatchOp(op="set", path="elements.accent_bar.x", value=14.0)
    patched = apply_patch(spec_with_id, [edit_op])

    assert patched.elements[0].x == 14.0


def test_patch_set_nested_theme_color(base_spec: DesignSpec):
    """Set a nested theme color value."""
    op = PatchOp(op="set", path="theme.colors.primary", value="#003366")
    patched = apply_patch(base_spec, [op])

    assert patched.theme.colors.primary == "#003366"
    assert base_spec.theme.colors.primary != "#003366"


def test_patch_add_element(base_spec: DesignSpec):
    """Add a new element to the elements list."""
    initial_count = len(base_spec.elements)
    new_element = {
        "id": "new_footer_rect",
        "type": "rect",
        "x": 7.0,
        "y": 80.0,
        "w": 46.0,
        "h": 4.0,
        "fill": "accent",
    }
    op = PatchOp(op="add", path="elements", value=new_element)
    patched = apply_patch(base_spec, [op])

    assert len(patched.elements) == initial_count + 1
    assert patched.elements[-1].id == "new_footer_rect"


def test_patch_remove_by_id(base_spec: DesignSpec):
    """Remove an element by its element id."""
    setup_op = PatchOp(op="set", path="elements.0.id", value="to_delete")
    spec_with_id = apply_patch(base_spec, [setup_op])
    initial_count = len(spec_with_id.elements)

    delete_op = PatchOp(op="remove", path="elements.to_delete")
    patched = apply_patch(spec_with_id, [delete_op])

    assert len(patched.elements) == initial_count - 1
    assert not any(getattr(el, "id", None) == "to_delete" for el in patched.elements)


def test_patch_remove_by_index(base_spec: DesignSpec):
    """Remove an element by numeric index."""
    initial_count = len(base_spec.elements)
    delete_op = PatchOp(op="remove", path="elements.0")
    patched = apply_patch(base_spec, [delete_op])

    assert len(patched.elements) == initial_count - 1


def test_patch_unknown_index_raises(base_spec: DesignSpec):
    """Accessing an out-of-bounds list index raises PatchError."""
    op = PatchOp(op="set", path="elements.999.x", value=10.0)
    with pytest.raises(PatchError, match="no element at index 999"):
        apply_patch(base_spec, [op])


def test_patch_unknown_key_raises(base_spec: DesignSpec):
    """Setting an unknown property on a dict/model raises PatchError."""
    op = PatchOp(op="set", path="theme.colors.nonexistent_color", value="#123456")
    with pytest.raises(PatchError, match="no property 'nonexistent_color'"):
        apply_patch(base_spec, [op])


def test_patch_invalid_color_raises(base_spec: DesignSpec):
    """Setting an invalid hex color string fails validation and raises PatchError."""
    op = PatchOp(op="set", path="theme.colors.primary", value="not-a-color")
    with pytest.raises(PatchError):
        apply_patch(base_spec, [op])


def test_patch_invalid_type_raises(base_spec: DesignSpec):
    """Adding an element with an invalid type fails validation and raises PatchError."""
    bad_element = {
        "type": "invalid_shape_type",
        "x": 10.0,
        "y": 10.0,
    }
    op = PatchOp(op="add", path="elements", value=bad_element)
    with pytest.raises(PatchError):
        apply_patch(base_spec, [op])


def test_patch_schema_version_protected(base_spec: DesignSpec):
    """Attempting to patch schema_version raises an error immediately."""
    with pytest.raises(ValueError, match="patching 'schema_version' is not allowed"):
        PatchOp(op="set", path="schema_version", value="2.0")


def test_patch_idempotency_immutability_on_failure(base_spec: DesignSpec):
    """If a patch in a sequence fails, the original spec remains completely untouched."""
    dump_before = base_spec.model_dump()

    ops = [
        PatchOp(op="set", path="theme.colors.primary", value="#003366"),
        PatchOp(op="set", path="invalid.path.does.not.exist", value=123),
    ]

    with pytest.raises(PatchError):
        apply_patch(base_spec, ops)

    assert base_spec.model_dump() == dump_before


def test_patch_duplicate_id_rejected(base_spec: DesignSpec):
    """Adding an element with an id that already exists raises PatchError."""
    setup_op = PatchOp(op="set", path="elements.0.id", value="dup_id")
    spec_with_id = apply_patch(base_spec, [setup_op])

    dup_element = {
        "id": "dup_id",
        "type": "rect",
        "x": 5.0,
        "y": 5.0,
        "w": 10.0,
        "h": 10.0,
        "fill": "accent",
    }
    add_op = PatchOp(op="add", path="elements", value=dup_element)

    with pytest.raises(PatchError, match="duplicate element id"):
        apply_patch(spec_with_id, [add_op])


def test_patch_set_zero_and_none_allowed(base_spec: DesignSpec):
    """Setting numeric 0 and None values works without being treated as missing."""
    # Set x to 0
    op_zero = PatchOp(op="set", path="elements.0.x", value=0)
    patched = apply_patch(base_spec, [op_zero])
    assert patched.elements[0].x == 0

    # Set optional id to None
    setup_id = PatchOp(op="set", path="elements.0.id", value="temp_id")
    spec_with_id = apply_patch(base_spec, [setup_id])
    assert spec_with_id.elements[0].id == "temp_id"

    op_none = PatchOp(op="set", path="elements.0.id", value=None)
    spec_cleared = apply_patch(spec_with_id, [op_none])
    assert spec_cleared.elements[0].id is None
