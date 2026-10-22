
from fastapi import HTTPException, UploadFile

from openapi_server.apis.analyze_api_base import BaseAnalyzeApi
from openapi_server.models.analysis_result import AnalysisResult

from analyzer import analyze_lines


class AnalyzeApi(BaseAnalyzeApi):
    async def analyze(self, file: UploadFile) -> AnalysisResult:
        content = await file.read()

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File is not valid UTF-8 text",
            )

        result = analyze_lines(text.splitlines())

        return AnalysisResult(**result)