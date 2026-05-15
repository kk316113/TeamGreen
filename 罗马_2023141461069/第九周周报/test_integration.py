# test_integration.py - 模拟 B-2 调用 B-3 的示例
import requests
import time

BASE_URL = "http://localhost:8000"

def submit_code(code, question_type, test_suite_id):
    resp = requests.post(f"{BASE_URL}/api/v1/evaluate", json={
        "submission_id": "test001",
        "code": code,
        "question_type": question_type,
        "test_suite_id": test_suite_id,
        "timeout": 5,
        "memory_limit_mb": 256
    })
    return resp.json()["task_id"]

def poll_result(task_id):
    while True:
        resp = requests.get(f"{BASE_URL}/api/v1/result/{task_id}")
        data = resp.json()
        if data["status"] in ("completed", "failed"):
            return data
        time.sleep(0.5)

if __name__ == "__main__":
    code = "print(sum(map(int, input().split())))"
    task_id = submit_code(code, "cmd", "ts_cmd_sum")
    result = poll_result(task_id)
    print("评分结果:", result)