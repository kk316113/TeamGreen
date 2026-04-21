"""
模型定义
此模块定义了应用程序中涉及的数据库实体（表）的 Python 类表示。
这些类继承自 database.Base，它们的属性对应数据库表的列。
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base # 导入声明基类
from datetime import datetime
import enum

# 定义问题类型的枚举，用于限制 problem_type 字段的值
class ProblemType(enum.Enum):
    CLI = "cli"         # 命令行输入输出模式
    FILE_IO = "file_io" # 文件输入输出模式
    API_CALL = "api_call" # 函数接口调用模式


# 题目表的 ORM 模型
class ProblemDB(Base):
    # 指定数据库中对应的表名
    __tablename__ = "problems"
    
    # 定义表的列（字段）
    id = Column(String(50), primary_key=True, index=True) # 题目唯一ID，设为主键并建立索引
    title = Column(String(255), nullable=False) # 题目标题，不允许为空
    description = Column(Text) # 题目描述，可以是较长的文本
    problem_type = Column(SQLEnum(ProblemType), nullable=False) # 题目类型，使用枚举约束
    difficulty = Column(Integer, default=1) # 难度级别，默认为1
    time_limit = Column(Integer, default=1000) # 时间限制（毫秒），默认1000ms
    memory_limit = Column(String(20), default="256m") # 内存限制，字符串形式，如 "256m"
    language = Column(String(50), default="python") # 编程语言，默认为python
    created_at = Column(DateTime, default=datetime.utcnow) # 创建时间，自动记录
    
    # 定义与其他表的关系
    # 一个题目可以有多个测试用例，back_populates 指定反向引用，cascade 设置级联删除
    test_cases = relationship("TestCaseDB", back_populates="problem", cascade="all, delete-orphan")
    # 一个题目对应一个配置，uselist=False 表示一对一关系，cascade 设置级联删除
    config = relationship("ProblemConfigDB", back_populates="problem", uselist=False, cascade="all, delete-orphan")

# 测试用例表的 ORM 模型
class TestCaseDB(Base):
    __tablename__ = "test_cases"
    
    id = Column(String(50), primary_key=True, index=True) # 测试用例唯一ID
    problem_id = Column(String(50), ForeignKey("problems.id"), nullable=False) # 外键，关联到题目表
    input_data = Column(Text, nullable=False) # 输入数据
    expected_output = Column(Text, nullable=False) # 期望的输出数据
    is_sample = Column(Boolean, default=False) # 是否为样例测试用例
    score_weight = Column(Integer, default=10) # 该测试用例的分值权重
    
    # 定义与题目表的反向关系
    problem = relationship("ProblemDB", back_populates="test_cases")

# 题目配置表的 ORM 模型
class ProblemConfigDB(Base):
    __tablename__ = "problem_configs"
    
    id = Column(String(50), primary_key=True, index=True) # 配置唯一ID
    problem_id = Column(String(50), ForeignKey("problems.id"), unique=True, nullable=False) # 外键，关联到题目表，且唯一
    entry_point = Column(String(100), nullable=True) # 程序入口点（如函数名），可为空
    input_filename = Column(String(50), default="input.txt") # 输入文件名，默认值
    output_filename = Column(String(50), default="output.txt") # 输出文件名，默认值
    
    # 定义与题目表的反向关系
    problem = relationship("ProblemDB", back_populates="config")