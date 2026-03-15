from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Project


def create_project(db: Session, name: str, description: str | None = None) -> Project:
    project = Project(name=name, description=description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: str) -> Project | None:
    return db.get(Project, project_id)


def list_projects(db: Session) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


def delete_project(db: Session, project_id: str) -> bool:
    project = db.get(Project, project_id)
    if not project:
        return False
    db.delete(project)
    db.commit()
    return True
