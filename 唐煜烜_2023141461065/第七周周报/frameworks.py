"""
测试框架模块：定义 CLI, FILE_IO, API_CALL 等不同模式的执行逻辑
此模块定义了一个抽象基类 BaseTestFramework 和三个具体的子类，
分别对应不同的题目类型（CLI, FILE_IO, API_CALL）。
每个子类实现了 execute_test 方法，定义了如何在一个测试用例上运行用户代码。
"""
import tempfile
import os
import asyncio
from abc import ABC, abstractmethod # 导入抽象基类和装饰器
from schemas import ProblemResponse, TestCaseResponse # 导入 Pydantic 模型
from security import SandboxSecurity # 导入沙盒安全模块

class BaseTestFramework(ABC):
    """
    抽象基类，定义了所有测试框架的通用接口。
    """
    def __init__(self, sandbox: SandboxSecurity):
        """
        初始化框架，接收一个沙盒实例用于安全执行代码。
        """
        self.sandbox = sandbox

    @abstractmethod
    async def execute_test(self, problem: ProblemResponse, submission_code: str, test_case: TestCaseResponse) -> dict:
        """
        抽象方法，必须由子类实现。
        用于执行一次针对特定问题、提交代码和测试用例的测试。
        :param problem: 题目信息
        :param submission_code: 用户提交的代码字符串
        :param test_case: 当前执行的测试用例
        :return: 包含测试结果的字典
        """
        pass

    def _compare_outputs(self, actual: str, expected: str) -> bool:
        """
        辅助方法，用于比较实际输出和期望输出。
        这里简单的去除首尾空白字符后比较，实际应用中可能需要更复杂的比较逻辑。
        """
        return actual.strip() == expected.strip()

class CommandLineTestFramework(BaseTestFramework):
    """
    命令行模式测试框架。
    用户代码通过标准输入接收数据，并将结果打印到标准输出。
    """
    async def execute_test(self, problem: ProblemResponse, submission_code: str, test_case: TestCaseResponse) -> dict:
        """
        执行 CLI 模式的测试。
        将用户代码写入临时文件，然后通过管道将测试用例的输入发送给它。
        """
        # 创建一个临时的 Python 文件来保存用户提交的代码
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(submission_code)
            script_path = f.name # 获取临时文件的路径

        try:
            # 构建命令：将测试用例的 input_data 作为输入，传给临时脚本
            command = f"echo '{test_case.input_data}' | python3 {script_path}"
            # 在沙盒中执行命令
            result = self.sandbox.run_command_sandbox(command, timeout=problem.time_limit, memory_limit=problem.memory_limit)
            actual_output = result.get('output', '')
            is_correct = self._compare_outputs(actual_output, test_case.expected_output)

            return {
                'test_case_id': test_case.id,
                'passed': is_correct,
                'actual_output': actual_output,
                'expected_output': test_case.expected_output,
                'execution_time': 0, # CLI 框架目前未精确计算执行时间
                'points_earned': test_case.score_weight if is_correct else 0,
                'error': result.get('error', '') if 'error' in result else (result.get('logs', '') if not result.get('success') else '')
            }
        finally:
            # 确保临时文件被删除
            os.unlink(script_path)

class FileInputTestFramework(BaseTestFramework):
    """
    文件输入输出模式测试框架。
    用户代码从指定文件读取输入，将结果写入指定文件。
    """
    async def execute_test(self, problem: ProblemResponse, submission_code: str, test_case: TestCaseResponse) -> dict:
        """
        执行 FILE_IO 模式的测试。
        将用户代码和测试用例的输入分别写入临时文件，然后执行用户代码。
        """
        # 创建临时的 Python 文件来保存用户提交的代码
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(submission_code)
            script_path = f.name

        try:
            # 创建临时的输入文件，写入测试用例的 input_data
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(test_case.input_data)
                input_file = f.name

            # 在沙盒中执行脚本，将 input_file 作为输入
            result = self.sandbox.run_file_sandbox(script_path, input_file, timeout=problem.time_limit, memory_limit=problem.memory_limit)
            actual_output = result.get('output', '')
            is_correct = self._compare_outputs(actual_output, test_case.expected_output)

            return {
                'test_case_id': test_case.id,
                'passed': is_correct,
                'actual_output': actual_output,
                'expected_output': test_case.expected_output,
                'execution_time': 0, # FILE_IO 框架目前未精确计算执行时间
                'points_earned': test_case.score_weight if is_correct else 0,
                'error': result.get('logs', '') if not result.get('success') else '' # 错误信息主要来自日志
            }
        finally:
            # 确保临时文件被删除
            os.unlink(script_path)
            os.unlink(input_file)

class InterfaceTestFramework(BaseTestFramework):
    """
    接口调用模式测试框架（简化版）。
    用户代码定义一个函数，测试时调用该函数并传入参数。
    """
    async def execute_test(self, problem: ProblemResponse, submission_code: str, test_case: TestCaseResponse) -> dict:
        """
        执行 API_CALL 模式的测试（简化示例）。
        将用户代码和测试逻辑合并到一个临时脚本中执行。
        注意：这里的 eval 实现非常不安全，仅用于演示。实际应用中应有更健壮的函数调用机制。
        """
        # 构建测试脚本：将用户代码和测试逻辑拼接在一起
        test_script = f"""
{submission_code} # 插入用户提交的代码

# 测试用例执行逻辑
try:
    test_input = {repr(test_case.input_data)} # 将输入数据作为 Python 对象
    # 这里应根据 problem.config.entry_point 来调用正确的函数
    # 例如：result = my_function(test_input)
    # 为了演示，这里使用 eval，但这极其危险！
    result = eval(test_input) if isinstance(eval(test_input), (int, float, str, list, dict, tuple, bool, type(None))) else str(eval(test_input))
    print(result) # 打印结果
except Exception as e:
    print(f"ERROR: {{e}}") # 捕获并打印异常
"""

        # 创建临时的测试脚本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            script_path = f.name

        try:
            # 在沙盒中执行测试脚本
            result = self.sandbox.run_command_sandbox(f"python3 {script_path}", timeout=problem.time_limit, memory_limit=problem.memory_limit)
            actual_output = result.get('output', '')
            is_correct = self._compare_outputs(actual_output, test_case.expected_output)

            return {
                'test_case_id': test_case.id,
                'passed': is_correct,
                'actual_output': actual_output,
                'expected_output': test_case.expected_output,
                'execution_time': 0, # API_CALL 框架目前未精确计算执行时间
                'points_earned': test_case.score_weight if is_correct else 0,
                'error': result.get('logs', '') if not result.get('success') else ''
            }
        finally:
            # 确保临时文件被删除
            os.unlink(script_path)