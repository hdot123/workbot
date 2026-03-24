---
type: [KB:GLOBAL]
title: 本地大模型技术基线规范
version: v1.1
created: 2026-03-07
tags: [llm, baseline, ollama, deployment, qwen]
status: superseded
scope: 仅适用于本地 Mac (M1/M4) 16GB 统一内存环境
last_verified: 2026-03-08
confidence: high
updated: 2026-03-24
related: []
source: Manual
---

# 本地大模型技术基线规范 (Local LLM Technical Baseline Specification)

> SOURCE MATERIAL ONLY
> 本文件继承自旧项目材料，仅作历史来源，不具备当前默认解释权。

> **适用范围**：仅本地 Mac (M1/M4) 16GB 统一内存环境
> **不适用**：阿里云节点 (node01/node-01) 不部署本地模型

## 1. 硬件运行基准 (Hardware Foundation)
- **内存策略**：显存占用上限锁定在 7.5 GB 以内，确保物理内存留白 > 40%，严禁触发系统交换 (Swap)。
- **算力分配**：执行全量 GPU 卸载 (Metal/CUDA)，禁止 CPU 参与 Token 生成计算。
- **存储要求**：模型权重及 KV Cache 必须存储于高速固态存储介质，加载时间应 < 5s。

## 2. 模型参数配置 (Inference Parameters)
| 参数名称 | 设定值 | 技术目的 |
| :--- | :--- | :--- |
| **num_ctx** | 4096 | 锁定上下文窗口，确保 16GB 环境下的显存余量。 |
| **num_gpu** | 32 (Max) | 强制全层加速，实现毫秒级首字响应 (TTFT)。 |
| **temperature** | 0.2 | 抑制采样随机性，确保结构化输出的一致性。 |
| **repeat_penalty** | 1.1 | 降低长文本识别中的逻辑死循环风险。 |
| **top_p** | 0.8 | 兼顾输出的严密性与语言自然度。 |

## 3. 逻辑指令基准 (System Logic)
- **核心职能**：仅执行文本去噪、干扰字符剔除、数据结构化还原。
- **去噪规范**：自动识别并过滤非目标字符（如批改痕迹、乱码、冗余坐标）。
- **输出格式**：严禁主观推测，必须严格遵循 `标识符 - 正文 - 内容` 层级结构。

## 4. 性能监控指标 (Health Metrics)
- **响应时延 (TTFT)**：首字延迟基准线 < 300ms。
- **吞吐速度 (TPS)**：生成速度基准线 35-50 tokens/s。
- **资源状态**：Swap 占用必须保持为 0；检测到 Swap > 100MB 须强制释放内存。

## 5. 异常处置协议 (Exception Handling)
- **长度溢出**：输入文本 > 4096 tokens 时，必须在接口层执行语义分段，禁止强行送入推理引擎。
- **逻辑溃败**：输出结果缺失关键标识符时，判定为逻辑幻觉，自动降温至 0.1 并重试一次。
- **任务熔断**：单次推理时长 > 30s 必须触发熔断，反馈负载过高。

## 6. 环境维护与部署 (Maintenance)
- **无状态性**：每次任务调用后需显式重置 Session 上下文，确保任务间逻辑隔离。
- **版本一致性**：多节点部署必须基于同一份 Modelfile 封装，严禁运行时手动修改参数。

## 7. 合规性要求 (Compliance)
- **强制适用**：本地 Mac 上部署的所有 LLM 必须遵守本规范。
- **例外审批**：任何参数偏离需记录到 `memory/kb/decisions/` 并说明理由。
- **定期审计**：每月检查本地模型配置一致性。
