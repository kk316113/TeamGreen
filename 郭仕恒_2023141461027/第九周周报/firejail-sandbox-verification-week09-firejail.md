# AutoGrader Firejail 沙箱验证记录

## 验证环境

- sandbox: `firejail`
- firejail_bin: `firejail`
- firejail_available: `False`
- memory_mb: `128`
- cpu_seconds: `2`
- nproc: `64`
- fsize_mb: `16`

## 验证结果

| 验证项 | 结果 | 说明 |
|---|---|---|
| static_forbidden_import | 通过 | 禁止导入模块: os |
| static_forbidden_call | 通过 | 禁止调用函数: eval |
| cli_case | 通过 | RE: Firejail sandbox is enabled but not available. Install firejail on Linux/WSL or set AUTOGRADER_JUDGE_SANDBOX=local. |
| file_case | 通过 | RE: Firejail sandbox is enabled but not available. Install firejail on Linux/WSL or set AUTOGRADER_JUDGE_SANDBOX=local. |
| function_case | 通过 | RE: Firejail sandbox is enabled but not available. Install firejail on Linux/WSL or set AUTOGRADER_JUDGE_SANDBOX=local. |
| assertion_case | 通过 | RE: Firejail sandbox is enabled but not available. Install firejail on Linux/WSL or set AUTOGRADER_JUDGE_SANDBOX=local. |
| timeout_case | 通过 | RE: Firejail sandbox is enabled but not available. Install firejail on Linux/WSL or set AUTOGRADER_JUDGE_SANDBOX=local. |

## 阶段结论

本次共执行 7 项验证，通过 7 项。
当前环境未安装 Firejail，验证重点为 Firejail 不可用时的受控错误返回；完整隔离效果需在 Linux/WSL 环境安装 Firejail 后继续验证。
