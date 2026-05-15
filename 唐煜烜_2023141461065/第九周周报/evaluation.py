"""
评价生成模块：根据测试结果计算分数和提供建议
此模块接收来自测试框架的详细结果列表，计算总体得分、准确率等指标，
并根据结果生成对学生的反馈建议。
"""
from typing import List

class EvaluationGenerator:
    @staticmethod
    def generate_evaluation(results: List[dict], total_points: float) -> dict:
        """
        根据测试结果和总分计算最终的评价报告。
        :param results: 测试框架返回的详细结果列表
        :param total_points: 所有测试用例的总分权重之和
        :return: 包含评分和分析的字典
        """
        # 计算通过的测试用例数量
        passed_tests = sum(1 for r in results if r['passed'])
        total_tests = len(results)
        # 计算获得的总分
        earned_points = sum(r['points_earned'] for r in results)
        # 计算通过率和得分百分比
        accuracy = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        # 生成反馈建议
        suggestions = EvaluationGenerator._generate_suggestions(results)

        return {
            'overall_score': round(score_percentage, 2), # 总体得分百分比，保留两位小数
            'total_points': total_points,
            'earned_points': earned_points,
            'accuracy_rate': round(accuracy, 2), # 通过率，保留两位小数
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'suggestions': suggestions, # 反馈建议列表
            'detailed_results': results # 详细的每项测试结果
        }

    @staticmethod
    def _generate_suggestions(results: List[dict]) -> List[str]:
        """
        根据测试结果生成反馈建议。
        :param results: 测试结果列表
        :return: 建议列表
        """
        suggestions = []
        # 找出所有失败的测试用例
        failed_tests = [r for r in results if not r['passed']]
        if failed_tests:
            suggestions.append(f"有 {len(failed_tests)} 个测试用例未通过，请检查代码逻辑")
        # 检查是否有任何输出
        if not any(r['actual_output'].strip() for r in results):
            suggestions.append("代码可能没有产生预期输出，请检查print语句")
        # 检查是否有错误日志
        if any(len(r.get('error', '')) > 0 for r in results):
            suggestions.append("代码存在运行时错误，请检查异常处理")
        # 如果以上都没有问题，则给予积极反馈
        if len(suggestions) == 0:
            suggestions.append("代码表现优秀，所有测试用例均已通过！")
        return suggestions