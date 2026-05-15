# 第九周 Firejail 沙箱任务总结

整理日期：2026-05-12

## 本周任务目标

第九周暂不推进 B-1/B-2/B-3/B-4 完整联调，优先完成沙箱相关工作。目标是让沙箱任务从“方案说明”推进到“可重复验证”，并形成周报可对应的成果物。

## 本周完成内容

1. 新增沙箱验证脚本：`demo/backend/scripts/verify_sandbox.py`
   - 支持 `--sandbox local`
   - 支持 `--sandbox firejail`
   - 支持输出 Markdown 验证报告

2. 完成 local 模式验证
   - 静态检查：禁止危险 import
   - 静态检查：禁止危险函数调用
   - 命令行输入题验证
   - 文件读写题验证
   - 函数调用题验证
   - 断言测试题验证
   - 超时 TLE 验证

3. 完成 Firejail 不可用场景验证
   - 当前 Windows 环境未安装 Firejail
   - 强制切换 `AUTOGRADER_JUDGE_SANDBOX=firejail` 后，评测不会导致后端崩溃
   - 系统会返回明确提示：需要在 Linux/WSL 安装 Firejail，或切回 local 模式

4. 生成两份验证报告
   - `demo/docs/firejail-sandbox-verification-week09-local.md`
   - `demo/docs/firejail-sandbox-verification-week09-firejail.md`

## 验证结果概览

| 验证模式 | 验证项数量 | 通过情况 | 说明 |
|---|---:|---|---|
| local | 7 | 7/7 通过 | 基础评测链路和静态安全检查可运行 |
| firejail | 7 | 7/7 通过 | 当前环境未安装 Firejail，验证重点为受控错误返回 |

## 当前结论

当前 Demo 已经具备以下沙箱相关能力：

- 有基础静态安全检查；
- 有 local/firejail 两种评测执行模式配置；
- 有 Firejail 资源限制参数配置；
- 有可重复执行的沙箱验证脚本；
- 在 Firejail 不可用时能够受控返回错误，不会导致后端崩溃。

需要注意的是：当前 Windows 本地环境无法完成 Firejail 的真实隔离运行验证。因此，不能表述为“Firejail 沙箱已经完整部署完成”。更准确的表述是：

> 当前 Demo 已完成 Firejail 沙箱接入方案、配置项和验证脚本；本地已验证基础评测链路与 Firejail 不可用时的受控错误处理。后续将在 Linux/WSL 环境中继续验证完整隔离效果。

## 后续计划

1. 准备 WSL Ubuntu 或 Linux 服务器环境。
2. 安装 Firejail。
3. 设置 `AUTOGRADER_JUDGE_SANDBOX=firejail`。
4. 重新执行 `verify_sandbox.py --sandbox firejail`。
5. 增加网络访问、文件越界访问、进程数量、超大输出等异常场景验证。
