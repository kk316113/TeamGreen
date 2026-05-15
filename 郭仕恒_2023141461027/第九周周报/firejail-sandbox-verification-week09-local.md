# AutoGrader Firejail 沙箱验证记录

## 验证环境

- sandbox: `local`
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
| cli_case | 通过 | AC: 7 |
| file_case | 通过 | AC: 3 |
| function_case | 通过 | AC: 42 |
| assertion_case | 通过 | AC: pass |
| timeout_case | 通过 | TLE: 运行时间超过限制 |

## 阶段结论

本次共执行 7 项验证，通过 7 项。
当前为 local 模式验证，主要确认评测链路与基础安全检查可运行；Firejail 完整隔离需切换到 firejail 模式后验证。
