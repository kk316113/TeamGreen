from pydantic import BaseModel
from typing import Dict, Any, Optional

class SubmissionRequest(BaseModel):
    submission_id: str
    code: str
    language: str = "python"          # python / javascript
    question_type: str                # cmd, file, api
    test_suite_id: str
    timeout: int = 5
    memory_limit_mb: int = 256

class TaskStatus(BaseModel):
    task_id: str
    status: str                       # queued, running, completed, failed

class TestCase(BaseModel):
    input: str
    expected: str

class TestSuite(BaseModel):
    type: str                         # cmd, file, api
    cases: Dict[str, TestCase]