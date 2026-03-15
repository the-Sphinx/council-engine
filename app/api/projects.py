from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import ErrorResponse, ProjectCreate, ProjectResponse
from app.services.project_service import create_project, get_project, list_projects

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project_endpoint(body: ProjectCreate, db: Session = Depends(get_db)):
    project = create_project(db, name=body.name, description=body.description)
    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects_endpoint(db: Session = Depends(get_db)):
    return list_projects(db)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_endpoint(project_id: str, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Project {project_id} not found"},
        )
    return project
