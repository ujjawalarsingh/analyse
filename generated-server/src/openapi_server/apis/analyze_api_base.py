# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictBytes, StrictStr
from typing import Any, Tuple, Union
from typing_extensions import Annotated
from openapi_server.models.analysis_result import AnalysisResult
from fastapi import File, UploadFile


class BaseAnalyzeApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAnalyzeApi.subclasses = BaseAnalyzeApi.subclasses + (cls,)
    async def analyze(
        self,
        file: UploadFile,
    ) -> AnalysisResult:
        """Upload a log file using multipart/form-data and get ERROR counts per service. """
        ...
