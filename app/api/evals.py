import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import EvalRunRequest, EvalRunResponse

router = APIRouter(prefix="/evals", tags=["evals"])


@router.post("/run", response_model=EvalRunResponse, status_code=202)
def run_eval(body: EvalRunRequest, db: Session = Depends(get_db)):
    """
    Trigger an offline evaluation run.
    This runs synchronously (V1 has no background task queue).
    """
    eval_path = Path(body.eval_dataset_path)
    if not eval_path.exists():
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "message": f"Eval dataset not found: {eval_path}"},
        )

    from app.main import get_pipeline_for_project, get_generator, get_verifier
    try:
        pipeline = get_pipeline_for_project(body.project_id)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail={"error": "index_not_found", "message": f"No index for project {body.project_id}"},
        )

    from app.evaluation.runner import run_eval as _run_eval
    run_id = str(uuid.uuid4())
    output_path = f"data/eval_runs/eval_{run_id}.json"

    _run_eval(
        project_id=body.project_id,
        eval_dataset_path=eval_path,
        db=db,
        pipeline=pipeline,
        generator=get_generator(),
        verifier=get_verifier(),
        run_id=run_id,
        label=body.label,
        output_path=Path(output_path),
    )

    return EvalRunResponse(
        run_id=run_id,
        label=body.label,
        status="completed",
        output_path=output_path,
    )


@router.get("/{run_id}/results")
def get_eval_results(run_id: str):
    result_path = Path(f"data/eval_runs/eval_{run_id}.json")
    if not result_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Eval run {run_id} not found"},
        )
    import json
    return json.loads(result_path.read_text())
