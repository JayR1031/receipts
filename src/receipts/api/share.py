"""`GET /share/{run_id}`: a finished run's battlecard as a public, read-only HTML page.

It returns nothing `GET /api/runs/{run_id}` does not already return to anyone with the run id;
the page itself (meta tags for link previews, `noindex`) is L5's `receipts.ui.share`. Not in
the OpenAPI document: it is a page, not part of the API.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, Response

from receipts.api.routes import ServiceDep
from receipts.contracts import RunId
from receipts.ui.share import (
    SHARE_IMAGE_PATH,
    render_missing_page,
    render_share_page,
    share_image,
)

router = APIRouter(include_in_schema=False)

_CACHE_IMAGE = {"Cache-Control": "public, max-age=86400"}
_CACHE_PAGE = {"Cache-Control": "public, max-age=300"}


@router.get(SHARE_IMAGE_PATH)
def share_card_image() -> Response:
    return Response(share_image(), media_type="image/png", headers=_CACHE_IMAGE)


@router.get("/share/{run_id}", response_class=HTMLResponse)
async def share_page(run_id: str, request: Request, service: ServiceDep) -> HTMLResponse:
    host = request.url.netloc
    card = await service.get(RunId(run_id))
    if card is None:
        return HTMLResponse(render_missing_page(host=host), status_code=status.HTTP_404_NOT_FOUND)
    return HTMLResponse(render_share_page(card, host=host), headers=_CACHE_PAGE)
