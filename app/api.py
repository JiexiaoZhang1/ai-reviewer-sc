"""FastAPI entrypoint for the AI reviewer agent."""

from __future__ import annotations

import zipfile
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .report import ReportGenerationError, analyze_repository
from .storage import unpack_zip_file

app = FastAPI(title="AI Reviewer Agent", version="0.1.0")


@app.post("/analyze")
async def analyze(
    problem_description: str = Form(..., description="Project requirements to analyze against."),
    code_zip: UploadFile = File(..., description="Zip archive containing the project source code."),
    settings: Settings = Depends(get_settings),
):
    if not code_zip.filename or not code_zip.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .zip archive.")

    try:
        with unpack_zip_file(code_zip) as repo_path:
            report = analyze_repository(problem_description, repo_path, settings)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid zip archive.") from exc
    except ReportGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await code_zip.close()

    return JSONResponse(content=report)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
