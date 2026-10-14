"""Design Spec modification and patch routes."""
from fastapi import APIRouter

from app.api.models import PatchRequest, PatchResponse
from app.refine.patch import apply_patch

router = APIRouter(prefix="/spec", tags=["spec"])


@router.post("/patch", response_model=PatchResponse)
def patch_spec(payload: PatchRequest) -> PatchResponse:
    """Apply discrete patch operations to a DesignSpec and return the updated spec."""
    updated = apply_patch(payload.spec, payload.ops)
    return PatchResponse(spec=updated)
