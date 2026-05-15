"""
题库管理器：负责题目的增删改查和提交评分
此模块是业务逻辑的核心，它与数据库交互（通过 ORM 模型），
调用测试框架执行评测，并使用评价生成器产生最终报告。
"""
import hashlib
from typing import Optional, List
from sqlalchemy.orm import Session # 导入 SQLAlchemy 会话类型
from models import ProblemDB, TestCaseDB, ProblemType # 导入 ORM 模型
from schemas import ProblemCreate, ProblemUpdate, ProblemResponse, TestCaseResponse, SubmissionResult # 导入 Pydantic 模型
from frameworks import BaseTestFramework, CommandLineTestFramework, FileInputTestFramework, InterfaceTestFramework # 导入测试框架
from security import SandboxSecurity # 导入沙盒安全模块
from evaluation import EvaluationGenerator # 导入评价生成模块
from datetime import datetime

class ProblemManager:
    def __init__(self, db: Session):
        """
        初始化管理器，接收一个数据库会话。
        初始化测试框架映射字典，根据题目类型选择合适的框架。
        初始化评价生成器实例。
        """
        self.db = db
        sandbox = SandboxSecurity() # 创建沙盒实例
        # 根据 ProblemType 映射到对应的测试框架实例
        self.test_frameworks: dict[ProblemType, BaseTestFramework] = {
            ProblemType.CLI: CommandLineTestFramework(sandbox),
            ProblemType.FILE_IO: FileInputTestFramework(sandbox),
            ProblemType.API_CALL: InterfaceTestFramework(sandbox)
        }
        self.evaluation_generator = EvaluationGenerator()

    def add_problem(self, problem: ProblemCreate):
        """
        添加新题目到数据库。
        :param problem: 从 API 接收的 ProblemCreate 模型实例
        :return: 创建成功的 ORM 模型实例
        """
        # 将 Pydantic 模型转换为 ORM 模型实例
        db_problem = ProblemDB(
            id=problem.id,
            title=problem.title,
            description=problem.description,
            problem_type=problem.problem_type,
            difficulty=problem.difficulty,
            time_limit=problem.time_limit,
            memory_limit=problem.memory_limit,
            language=problem.language
        )
        # 添加关联的测试用例
        for tc in problem.test_cases:
            db_tc = TestCaseDB(
                id=tc.id,
                problem_id=problem.id,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                is_sample=tc.is_sample,
                score_weight=tc.score_weight
            )
            db_problem.test_cases.append(db_tc) # 添加到 ORM 关系中

        # 将新的 ORM 实例添加到会话并提交到数据库
        self.db.add(db_problem)
        self.db.commit()
        self.db.refresh(db_problem) # 刷新 ORM 实例，使其包含数据库生成的 ID 等信息
        return db_problem

    def get_problem(self, problem_id: str) -> Optional[ProblemDB]:
        """
        根据 ID 获取题目。
        :param problem_id: 题目ID
        :return: ORM 模型实例或 None
        """
        return self.db.query(ProblemDB).filter(ProblemDB.id == problem_id).first()

    def list_problems(self) -> List[ProblemDB]:
        """
        获取所有题目列表。
        :return: ORM 模型实例列表
        """
        return self.db.query(ProblemDB).all()

    def update_problem(self, problem_id: str, problem_update: ProblemUpdate) -> Optional[ProblemDB]:
        """
        更新题目信息。
        :param problem_id: 要更新的题目ID
        :param problem_update: 包含更新信息的 Pydantic 模型
        :return: 更新后的 ORM 模型实例或 None
        """
        db_problem = self.get_problem(problem_id)
        if db_problem:
            # 使用 dict(exclude_unset=True) 确保只有被明确设置的字段才被更新
            for key, value in problem_update.dict(exclude_unset=True).items():
                setattr(db_problem, key, value)
            self.db.commit()
            self.db.refresh(db_problem)
        return db_problem

    def delete_problem(self, problem_id: str) -> bool:
        """
        删除题目。
        :param problem_id: 要删除的题目ID
        :return: 删除是否成功
        """
        db_problem = self.get_problem(problem_id)
        if db_problem:
            self.db.delete(db_problem) # 由于在 models.py 中设置了 cascade，相关测试用例也会被删除
            self.db.commit()
            return True
        return False

    async def grade_submission(self, problem_id: str, submission_code: str, student_id: str) -> SubmissionResult:
        """
        对提交的代码进行评分。
        :param problem_id: 题目ID
        :param submission_code: 用户提交的代码字符串
        :param student_id: 学生ID
        :return: 包含评分结果的 SubmissionResult 模型实例
        """
        problem = self.get_problem(problem_id)
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        # 根据题目的类型选择对应的测试框架
        framework = self.test_frameworks[problem.problem_type]
        
        # 为题目中的每个测试用例创建一个异步任务
        tasks = [
            framework.execute_test(
                ProblemResponse.from_orm(problem), # 将 ORM 模型转为 Pydantic 模型供框架使用
                submission_code,
                TestCaseResponse.from_orm(tc) # 将 ORM 模型转为 Pydantic 模型
            )
            for tc in problem.test_cases
        ]
        # 并发执行所有测试用例的任务
        results = await asyncio.gather(*tasks)

        # 计算总分权重
        total_points = sum(tc.score_weight for tc in problem.test_cases)
        # 生成最终评价报告
        evaluation = self.evaluation_generator.generate_evaluation(results, total_points)

        # 生成唯一的提交ID
        submission_id = hashlib.md5(f"{problem_id}_{student_id}_{datetime.now()}".encode()).hexdigest()

        # 返回最终的评分结果模型
        return SubmissionResult(
            submission_id=submission_id,
            problem_id=problem_id,
            student_id=student_id,
            overall_score=evaluation['overall_score'],
            total_points=total_points,
            details=results,
            execution_time=0, # 当前未精确计算总执行时间
            created_at=datetime.now() # 记录评分完成的时间
        )