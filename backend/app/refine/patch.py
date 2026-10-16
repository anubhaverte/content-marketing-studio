"""Patch engine for applying discrete edit operations to a DesignSpec."""
import copy
from typing import Any

from pydantic import ValidationError

from app.spec.loader import _clean_path
from app.spec.schema import DesignSpec, PatchOp


class PatchError(Exception):
    """Raised when a patch operation cannot be applied or results in an invalid spec."""


def _traverse_to_parent(data: Any, segments: list[str], op_desc: str) -> tuple[Any, str]:
    """Traverse path segments up to the parent container of the final target.

    Returns:
        (parent_container, last_segment)
    """
    if not segments:
        raise PatchError(f"{op_desc}: empty path")

    curr = data
    for i, seg in enumerate(segments[:-1]):
        if isinstance(curr, dict):
            if seg not in curr:
                raise PatchError(f"{op_desc}: no property '{seg}'")
            curr = curr[seg]
        elif isinstance(curr, list):
            if seg.isdigit():
                idx = int(seg)
                if not (0 <= idx < len(curr)):
                    raise PatchError(f"{op_desc}: no element at index {idx}")
                curr = curr[idx]
            else:
                found = None
                for item in curr:
                    if isinstance(item, dict) and item.get("id") == seg:
                        found = item
                        break
                if found is None:
                    raise PatchError(f"{op_desc}: no element with id '{seg}'")
                curr = found
        else:
            raise PatchError(f"{op_desc}: cannot traverse into non-container at segment '{seg}'")

    return curr, segments[-1]


def _resolve_target(data: Any, segments: list[str], op_desc: str) -> Any:
    """Resolve the target object pointed to by all path segments."""
    curr = data
    for seg in segments:
        if isinstance(curr, dict):
            if seg not in curr:
                raise PatchError(f"{op_desc}: no property '{seg}'")
            curr = curr[seg]
        elif isinstance(curr, list):
            if seg.isdigit():
                idx = int(seg)
                if not (0 <= idx < len(curr)):
                    raise PatchError(f"{op_desc}: no element at index {idx}")
                curr = curr[idx]
            else:
                found = None
                for item in curr:
                    if isinstance(item, dict) and item.get("id") == seg:
                        found = item
                        break
                if found is None:
                    raise PatchError(f"{op_desc}: no element with id '{seg}'")
                curr = found
        else:
            raise PatchError(f"{op_desc}: cannot traverse into non-container at segment '{seg}'")
    return curr


def apply_patch(spec: DesignSpec, ops: list[PatchOp]) -> DesignSpec:
    """Apply a list of patch operations in order to a DesignSpec.

    Works on a deep JSON dump of the spec so the input spec is never mutated.
    Returns a new validated DesignSpec.
    Raises PatchError if any path is unknown or if the resulting spec fails validation.
    """
    data = copy.deepcopy(spec.model_dump(mode="json"))

    for idx, op in enumerate(ops, start=1):
        op_desc = f"op {idx} ({op.op} {op.path})"
        path_str = op.path.strip()

        if path_str == "schema_version" or path_str.startswith("schema_version."):
            raise PatchError(f"{op_desc}: patching 'schema_version' is not allowed")

        segments = [s for s in path_str.split(".") if s]
        if not segments:
            raise PatchError(f"{op_desc}: empty path")

        if op.op == "add":
            target = _resolve_target(data, segments, op_desc)
            if not isinstance(target, list):
                raise PatchError(f"{op_desc}: target at '{op.path}' is not a list")
            target.append(copy.deepcopy(op.value))

        elif op.op == "set":
            parent, last_seg = _traverse_to_parent(data, segments, op_desc)
            if isinstance(parent, dict):
                if last_seg not in parent:
                    raise PatchError(f"{op_desc}: no property '{last_seg}'")
                parent[last_seg] = copy.deepcopy(op.value)
            elif isinstance(parent, list):
                if last_seg.isdigit():
                    item_idx = int(last_seg)
                    if not (0 <= item_idx < len(parent)):
                        raise PatchError(f"{op_desc}: no element at index {item_idx}")
                    parent[item_idx] = copy.deepcopy(op.value)
                else:
                    found_idx = None
                    for i, item in enumerate(parent):
                        if isinstance(item, dict) and item.get("id") == last_seg:
                            found_idx = i
                            break
                    if found_idx is None:
                        raise PatchError(f"{op_desc}: no element with id '{last_seg}'")
                    parent[found_idx] = copy.deepcopy(op.value)
            else:
                raise PatchError(f"{op_desc}: target container is neither dict nor list")

        elif op.op == "remove":
            parent, last_seg = _traverse_to_parent(data, segments, op_desc)
            if isinstance(parent, list):
                if last_seg.isdigit():
                    item_idx = int(last_seg)
                    if not (0 <= item_idx < len(parent)):
                        raise PatchError(f"{op_desc}: no element at index {item_idx}")
                    del parent[item_idx]
                else:
                    found_idx = None
                    for i, item in enumerate(parent):
                        if isinstance(item, dict) and item.get("id") == last_seg:
                            found_idx = i
                            break
                    if found_idx is None:
                        raise PatchError(f"{op_desc}: no element with id '{last_seg}'")
                    del parent[found_idx]
            elif isinstance(parent, dict):
                if last_seg not in parent:
                    raise PatchError(f"{op_desc}: no property '{last_seg}'")
                del parent[last_seg]
            else:
                raise PatchError(f"{op_desc}: target container is neither dict nor list")

    # Validate final spec
    try:
        return DesignSpec.model_validate(data)
    except ValidationError as err:
        lines = [f"Patched spec has {err.error_count()} problem(s):"]
        for e in err.errors():
            path = _clean_path(e["loc"])
            msg = e["msg"].removeprefix("Value error, ")
            if e["type"] == "extra_forbidden":
                msg = "unknown property (check the spelling)"
            lines.append(f"  - {path}: {msg}")
        raise PatchError("\n".join(lines)) from err
