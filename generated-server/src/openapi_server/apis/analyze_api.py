# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.analyze_api_base import BaseAnalyzeApi
import openapi_server.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from pydantic import Field, StrictBytes, StrictStr
from typing import Any, Tuple, Union
from typing_extensions import Annotated
from openapi_server.models.analysis_result import AnalysisResult
from fastapi import File, UploadFile

router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/analyze",
    responses={
        200: {"model": AnalysisResult, "description": "Analysis result"},
        400: {"description": "File is not valid UTF-8 text"},
        422: {"description": "Missing or invalid file field"},
    },
    tags=["Analyze"],
    summary="Analyze a log file",
    response_model_by_alias=True,
)
async def analyze(
    file: UploadFile = File(..., description="A .log or .txt file to analyze.", alias="file"),
) -> AnalysisResult:
    """Upload a log file using multipart/form-data and get ERROR counts per service. """
    if not BaseAnalyzeApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAnalyzeApi.subclasses[0]().analyze(file)
