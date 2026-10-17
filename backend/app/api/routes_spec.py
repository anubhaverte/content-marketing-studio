"""Design Spec modification and patch routes."""
from fastapi import APIRouter, HTTPException

from app.api.models import PatchRequest, PatchResponse, RefineRequest, RefineResponse
from app.refine.nl_to_patch import nl_to_patch
from app.refine.patch import apply_patch
from app.spec.schema import PatchOp

router = APIRouter(prefix="/spec", tags=["spec"])


@router.post("/patch", response_model=PatchResponse)
def patch_spec(payload: PatchRequest) -> PatchResponse:
    """Apply discrete patch operations to a DesignSpec and return the updated spec."""
    updated = apply_patch(payload.spec, payload.ops)
    return PatchResponse(spec=updated)


@router.post("/refine", response_model=RefineResponse)
def refine_spec(payload: RefineRequest) -> RefineResponse:
    """Convert a natural-language refinement prompt into safe patch ops and return the updated spec."""
    raw_ops = nl_to_patch(payload.prompt, payload.spec)
    if not raw_ops:
        return RefineResponse(
            spec=payload.spec,
            ops=[],
            summary="No visual adjustments could be determined from the prompt. Design unchanged.",
        )

    patch_ops = [PatchOp(**op) for op in raw_ops]
    try:
        updated_spec = apply_patch(payload.spec, patch_ops)
    except Exception as err:
        raise HTTPException(status_code=422, detail=f"Failed applying refinement patch: {err}") from err

    summary = f"Applied {len(patch_ops)} visual adjustment(s): " + ", ".join(
        f"{op.path} -> {op.value}" for op in patch_ops[:3]
    )
    if len(patch_ops) > 3:
        summary += f" (+{len(patch_ops) - 3} more)"

    return RefineResponse(
        spec=updated_spec,
        ops=patch_ops,
        summary=summary,
    )

