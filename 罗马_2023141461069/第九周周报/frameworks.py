from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List
import json
from sandbox import SandboxExecutor

class TestFrameworkBase(ABC):
    """所有测试框架的抽象基类"""
    def __init__(self, code_path: Path, test_data: Dict[str, Any], sandbox: SandboxExecutor):
        self.code_path = code_path
        self.test_data = test_data
        self.sandbox = sandbox

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
        cmd = ["python3", str(self.code_path)]
        return self.sandbox.run(cmd, cwd=self.code_path.parent, stdin=input_data)


class FileTestFramework(TestFrameworkBase):
    def setup(self) -> bool:
        return True
    def run_test_case(self, case_id: str, input_data: str) -> Dict:
        input_file = self.code_path.parent / "input.txt"
        input_file.write_text(input_data)
        cmd = ["python3", str(self.code_path)]
        self.sandbox.run(cmd, cwd=self.code_path.parent, stdin="")
        output_file = self.code_path.parent / "output.txt"
        stdout = output_file.read_text() if output_file.exists() else ""
        return {"stdout": stdout, "stderr": "", "exit_code": 0}


class ApiTestFramework(TestFrameworkBase):
    """接口型"""
    def __init__(self, code_path: Path, test_data: Dict, sandbox: SandboxExecutor, function_name: str = "solve"):
        super().__init__(code_path, test_data, sandbox)
        self.function_name = function_name

    def setup(self) -> bool:
        wrapper = self.code_path.parent / "wrapper.py"
        wrapper.write_text(f"""
import sys, json, importlib.util
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