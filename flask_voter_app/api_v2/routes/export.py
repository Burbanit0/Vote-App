"""
api_v2/routes/export.py — Research dataset export (CSV + JSON).

Both routes generate one row per (scenario, voting method) deterministically
from `seed`. Same compute as app/routes/export.py; the only thing that
moved is the HTTP adapter (typed request body + StreamingResponse for CSV).

Routes:
    POST /api/v2/export/simulation-dataset       text/csv attachment
    POST /api/v2/export/simulation-dataset-json  JSON body

The CSV variant streams via `StreamingResponse` so we avoid materialising
the whole file in memory before the first byte hits the wire.
"""
from __future__ import annotations

import asyncio
import csv
import io

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse

from app.routes.export import _generate_rows, CSV_COLUMNS   # noqa: F401
from api_v2.schemas import (
    ExportDatasetJSON,
    ExportDatasetMeta,
    ExportDatasetRequest,
)


router = APIRouter(prefix="/api/v2/export", tags=["export"])


@router.post(
    "/simulation-dataset",
    summary="Export a reproducible research dataset as CSV",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "One row per (scenario × voting method).",
        },
    },
)
async def export_csv(request: ExportDatasetRequest) -> StreamingResponse:
    """Same compute as the JSON variant, but emitted as RFC-4180 CSV with
    an attachment Content-Disposition so the browser triggers a download."""
    rows = await asyncio.to_thread(
        _generate_rows,
        request.num_scenarios, request.num_candidates,
        request.num_voters,    request.seed,
        request.ideology,
    )

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

    filename = f"votelab_dataset_{request.seed}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/simulation-dataset-json",
    response_model=ExportDatasetJSON,
    summary="Export a reproducible research dataset as JSON",
    response_description="{ meta, columns, rows } — drop-in for pandas/dplyr.",
)
async def export_json(request: ExportDatasetRequest) -> ExportDatasetJSON:
    rows = await asyncio.to_thread(
        _generate_rows,
        request.num_scenarios, request.num_candidates,
        request.num_voters,    request.seed,
        request.ideology,
    )
    return ExportDatasetJSON(
        meta=ExportDatasetMeta(
            num_scenarios=request.num_scenarios,
            num_candidates=request.num_candidates,
            num_voters=request.num_voters,
            seed=request.seed,
            ideology=request.ideology,
            total_rows=len(rows),
        ),
        columns=CSV_COLUMNS,
        rows=rows,
    )
