# sandbox.py
import subprocess
import time
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any
from config import SANDBOX_TYPE, DEFAULT_TIMEOUT, DEFAULT_MEMORY_MB

logger = logging.getLogger("B3.sandbox")

class SandboxExecutor:
    """沙盒执行器 - 提供隔离环境运行不可信代码"""
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, memory_mb: int = DEFAULT_MEMORY_MB, sandbox_type: str = SANDBOX_TYPE):
        self.timeout = timeout
        self.memory_mb = memory_mb
        self.sandbox_type = sandbox_type
        self.firejail = shutil.which("firejail")
        self.nsjail = shutil.which("nsjail")
        if not self.firejail and not self.nsjail and sandbox_type != "subprocess":
            logger.warning("未找到安全沙盒工具，将使用不安全的 subprocess 降级模式（仅开发测试）")

    def run(self, cmd: List[str], cwd: Path, stdin: str = "") -> Dict[str, Any]:
        """
        在沙盒中执行命令，返回 stdout, stderr, exit_code, time_sec
        """
        start = time.time()
        # 构造沙盒命令前缀
        if self.sandbox_type == "firejail" and self.firejail:
            sandbox_cmd = [
                self.firejail,
                f"--timeout={self.timeout}",
                f"--rlimit-as={self.memory_mb}M",
                "--net=none",
                "--profile=/etc/firejail/default.profile",
                "--", *cmd
            ]
        elif self.sandbox_type == "nsjail" and self.nsjail:
            sandbox_cmd = [
                self.nsjail,
                "--time_limit", str(self.timeout),
                "--cpus", "1",
                "--mem_limit", f"{self.memory_mb}M",
                "--disable_proc",
                "--disable_net",
                "--chroot", "/",   # 生产环境需准备独立 rootfs
                "--", *cmd
            ]
        else:
            sandbox_cmd = cmd
            logger.warning("使用不安全的 subprocess 执行（无沙盒隔离）")

        try:
            proc = subprocess.run(
                sandbox_cmd, cwd=cwd, input=stdin,
                capture_output=True, text=True,
                timeout=self.timeout + 1,
                check=False
            )
            elapsed = time.time() - start
            logger.info(f"沙盒执行命令 {' '.join(cmd)} 耗时 {elapsed:.3f}s")
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "time_sec": round(elapsed, 3)
            }
        except subprocess.TimeoutExpired:
            logger.error(f"沙盒执行超时 (>{self.timeout}s) 命令: {cmd}")
            return {"stdout": "", "stderr": "Timeout", "exit_code": -1, "time_sec": self.timeout}
        except Exception as e:
            logger.exception(f"沙盒执行异常: {e}")
            return {"stdout": "", "stderr": str(e), "exit_code": -2, "time_sec": 0}