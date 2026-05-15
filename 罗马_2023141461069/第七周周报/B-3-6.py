import os
import sys
import subprocess
import tempfile
import uuid
import shutil
import time
import json
import logging
import sqlite3
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("B3")

DB_PATH = "autograder.db"
API_KEY = "your-secret-key-change-in-production"   # 实际应从环境变量读取

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT,
                result TEXT,
                error TEXT,
                created_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_suites (
                suite_id TEXT PRIMARY KEY,
                data TEXT
            )
        """)
init_db()

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True

class SandboxExecutor:
    """安全沙盒中间件 - 基于 Firejail（支持动态库隔离）"""
    def __init__(self, timeout: int = 5, memory_mb: int = 256):
        self.timeout = timeout
        self.memory_mb = memory_mb
        self.firejail = shutil.which("firejail")
        if not self.firejail:
            logger.error("Firejail 未安装，无法提供安全隔离")
            raise RuntimeError("Firejail is required for sandbox execution")

    def run(self, cmd: List[str], cwd: Path, stdin: str = "") -> Dict[str, Any]:
        """在 Firejail 沙盒中执行命令，返回 stdout/stderr/exit_code/time_sec"""
        firejail_cmd = [
            self.firejail,
            f"--timeout={self.timeout}",
            f"--rlimit-as={self.memory_mb}M",
            "--net=none",
            "--profile=/etc/firejail/default.profile",
            "--", *cmd
        ]
        start = time.time()
        try:
            proc = subprocess.run(
                firejail_cmd,
                cwd=cwd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=self.timeout + 1,
                check=False
            )
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "time_sec": round(time.time() - start, 3)
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Timeout exceeded", "exit_code": -1, "time_sec": self.timeout}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "exit_code": -2, "time_sec": 0}

def static_security_check(code: str, language: str) -> Optional[str]:
    """静态扫描危险函数，防止恶意代码"""
    dangerous_patterns = {
        "python": [
            r"os\.system", r"subprocess\.", r"eval\(", r"exec\(", r"__import__",
            r"open\(.*['\"]w['\"]\)", r"shutil\.", r"socket\.", r"requests\."
        ],
        "javascript": [
            r"require\(['\"]child_process['\"]\)", r"eval\(", r"process\.env",
            r"fs\.writeFile", r"http\.request"
        ]
    }
    patterns = dangerous_patterns.get(language, [])
    for pat in patterns:
        if re.search(pat, code):
            return f"Security violation: {pat} found in code"
    return None

class TestFrameworkBase(ABC):
    def __init__(self, code_path: Path, test_data: Dict[str, Any], sandbox: SandboxExecutor, language: str):
        self.code_path = code_path
        self.test_data = test_data
        self.sandbox = sandbox
        self.language = language

    @abstractmethod
    def setup(self) -> bool:
        pass

    @abstractmethod
    def run_test_case(self, case_id: str, input_data: str) -> Dict:
        pass

    def validate_output(self, actual: str, expected: str) -> bool:
        return actual.strip() == expected.strip()

    def collect_results(self, results: List[Dict]) -> Dict:
        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        details = [
            {
                "case_id": r['case_id'],
                "passed": r['passed'],
                "actual": r.get('actual', ''),
                "expected": r.get('expected', ''),
                "error_msg": r.get('error_msg', '')
            } for r in results
        ]
        score = (passed / total * 100) if total else 0
        return {
            "overall": {"score": round(score, 2), "summary": f"通过 {passed}/{total} 个用例"},
            "details": details
        }

    def run_all(self) -> Dict:
        if not self.setup():
            return {"error": "环境准备失败"}
        results = []
        for case_id, data in self.test_data.items():
            out = self.run_test_case(case_id, data['input'])
            passed = self.validate_output(out['stdout'], data['expected'])
            results.append({
                "case_id": case_id,
                "passed": passed,
                "actual": out['stdout'],
                "expected": data['expected'],
                "error_msg": out['stderr']
            })
        return self.collect_results(results)

class CmdTestFramework(TestFrameworkBase):
    def setup(self) -> bool:
        return True

    def run_test_case(self, case_id: str, input_data: str) -> Dict:
        if self.language == "python":
            cmd = ["python3", str(self.code_path)]
        elif self.language == "javascript":
            cmd = ["node", str(self.code_path)]
        else:
            return {"stdout": "", "stderr": "Unsupported language", "exit_code": 1}
        return self.sandbox.run(cmd, cwd=self.code_path.parent, stdin=input_data)

class FileTestFramework(TestFrameworkBase):
    def setup(self) -> bool:
        return True

    def run_test_case(self, case_id: str, input_data: str) -> Dict:
        input_file = self.code_path.parent / "input.txt"
        input_file.write_text(input_data)
        if self.language == "python":
            cmd = ["python3", str(self.code_path)]
        elif self.language == "javascript":
            cmd = ["node", str(self.code_path)]
        else:
            return {"stdout": "", "stderr": "Unsupported language", "exit_code": 1}
        self.sandbox.run(cmd, cwd=self.code_path.parent, stdin="")
        output_file = self.code_path.parent / "output.txt"
        stdout = output_file.read_text() if output_file.exists() else ""
        return {"stdout": stdout, "stderr": "", "exit_code": 0}

class ApiTestFramework(TestFrameworkBase):
    def __init__(self, code_path: Path, test_data: Dict, sandbox: SandboxExecutor, language: str, function_name: str = "solve"):
        super().__init__(code_path, test_data, sandbox, language)
        self.function_name = function_name

    def setup(self) -> bool:
        if self.language != "python":
            logger.error("API测试框架目前仅支持Python")
            return False
        wrapper = self.code_path.parent / "wrapper.py"
        wrapper.write_text(f"""
import sys, json, importlib.util, traceback
spec = importlib.util.spec_from_file_location("student", "{self.code_path}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
func = getattr(mod, "{self.function_name}")
data = sys.stdin.read()
args = json.loads(data)
if isinstance(args, list):
    result = func(*args)
else:
    result = func(**args)
if result is not None:
    print(result)
""")
        return True

    def run_test_case(self, case_id: str, input_data: str) -> Dict:
        cmd = ["python3", str(self.code_path.parent / "wrapper.py")]
        return self.sandbox.run(cmd, cwd=self.code_path.parent, stdin=input_data)

app = FastAPI(title="AutoGrader B-3 - 安全测评中间件")

class SubmissionRequest(BaseModel):
    submission_id: str
    code: str
    language: str = "python"
    question_type: str          # cmd, file, api
    test_suite_id: str
    timeout: int = 5
    memory_limit_mb: int = 256

class TaskStatus(BaseModel):
    task_id: str
    status: str

def save_task(task_id: str, status: str, result: Any = None, error: str = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tasks (task_id, status, result, error, created_at) VALUES (?,?,?,?,?)",
            (task_id, status, json.dumps(result) if result else None, error, time.time())
        )

def load_task(task_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT status, result, error FROM tasks WHERE task_id = ?", (task_id,))
        row = cur.fetchone()
        if row:
            return {"status": row[0], "result": json.loads(row[1]) if row[1] else None, "error": row[2]}
    return None

def load_test_suite(suite_id: str) -> Optional[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT data FROM test_suites WHERE suite_id = ?", (suite_id,))
        row = cur.fetchone()
        return json.loads(row[0]) if row else None

def save_test_suite(suite_id: str, data: Dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO test_suites (suite_id, data) VALUES (?,?)", (suite_id, json.dumps(data)))

def run_evaluation(task_id: str, req: SubmissionRequest):
    save_task(task_id, "running")
    try:
        # 静态安全检测
        security_err = static_security_check(req.code, req.language)
        if security_err:
            raise ValueError(security_err)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ext = ".py" if req.language == "python" else ".js"
            code_file = tmp_path / f"code{ext}"
            code_file.write_text(req.code)

            suite = load_test_suite(req.test_suite_id)
            if not suite:
                raise ValueError("测试套件不存在")
            test_data = suite.get("cases", {})
            sandbox = SandboxExecutor(timeout=req.timeout, memory_mb=req.memory_limit_mb)

            if req.question_type == "cmd":
                framework = CmdTestFramework(code_file, test_data, sandbox, req.language)
            elif req.question_type == "file":
                framework = FileTestFramework(code_file, test_data, sandbox, req.language)
            elif req.question_type == "api":
                framework = ApiTestFramework(code_file, test_data, sandbox, req.language, function_name="solve")
            else:
                raise ValueError(f"未知题型: {req.question_type}")

            result = framework.run_all()
            save_task(task_id, "completed", result=result)
            logger.info(f"任务 {task_id} 完成，得分 {result.get('overall',{}).get('score',0)}")
    except Exception as e:
        logger.exception(f"任务 {task_id} 失败")
        save_task(task_id, "failed", error=str(e))

@app.post("/api/v1/evaluate", response_model=TaskStatus, dependencies=[Depends(verify_api_key)])
async def evaluate(req: SubmissionRequest, background_tasks: BackgroundTasks):
    suite = load_test_suite(req.test_suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="测试套件不存在")
    if suite.get("type") != req.question_type:
        raise HTTPException(status_code=400, detail="题型与测试套件不匹配")

    task_id = str(uuid.uuid4())
    save_task(task_id, "queued")
    background_tasks.add_task(run_evaluation, task_id, req)
    logger.info(f"提交任务 {task_id}，题型 {req.question_type}")
    return TaskStatus(task_id=task_id, status="queued")

@app.get("/api/v1/result/{task_id}")
async def get_result(task_id: str):
    task = load_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task["status"] == "completed":
        return {"status": "completed", **task["result"]}
    elif task["status"] == "failed":
        return {"status": "failed", "error": task["error"]}
    else:
        return {"status": task["status"]}

@app.get("/api/v1/result/{task_id}/export")
async def export_result(task_id: str):
    task = load_task(task_id)
    if not task or task["status"] != "completed":
        raise HTTPException(status_code=404, detail="结果不存在或未完成")
    from fastapi.responses import FileResponse
    export_file = Path(f"/tmp/{task_id}_result.json")
    export_file.write_text(json.dumps(task["result"], indent=2, ensure_ascii=False))
    return FileResponse(export_file, filename=f"{task_id}_result.json", media_type="application/json")

@app.get("/api/v1/test-suites")
async def list_suites():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT suite_id FROM test_suites")
        return [row[0] for row in cur.fetchall()]

@app.post("/api/v1/test-suites/{suite_id}")
async def create_or_update_suite(suite_id: str, suite: Dict):
    if "cases" not in suite:
        raise HTTPException(status_code=400, detail="缺少 cases 字段")
    save_test_suite(suite_id, suite)
    return {"status": "ok"}

@app.delete("/api/v1/test-suites/{suite_id}")
async def delete_suite(suite_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM test_suites WHERE suite_id = ?", (suite_id,))
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "alive"}

if __name__ == "__main__":
    import uvicorn
    # 初始化示例题库（如果不存在）
    if not load_test_suite("ts_cmd_sum"):
        sample = {
            "type": "cmd",
            "cases": {
                "case1": {"input": "1 2\n", "expected": "3\n"},
                "case2": {"input": "10 20\n", "expected": "30\n"}
            }
        }
        save_test_suite("ts_cmd_sum", sample)
        logger.info("已创建示例测试套件 ts_cmd_sum")
    logger.info("启动沙盒安全中间件及测评API服务，文档: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)