# 项目经验教训志：神经符号物理求解器

> 本文档是对项目开发全过程的深度技术复盘，详细记录了在构建多智能体 AI 系统以求解复杂数学积分的过程中所遇到的每一个重大挑战、策略转变和经验教训。

---

## 1. 项目起源：核心构想

本项目的基本假设看似简单：**我们能否让 AI 逐步"推导"出数学证明，而非仅仅猜测答案？**

大型语言模型 (LLM) 容易产生"幻觉跳跃"——它们经常从题目声明直接跳到最终答案，编造出数学上无效的中间步骤。我们的解决方案是强制执行**原子步骤 (Atomic Step)** 约束：AI（理论智能体）每次只允许提出*一个单一的数学操作*。然后，一个独立的确定性引擎（数值 Oracle）在下一步探索之前*验证*每一步。这创建了一个 AI 充当"探索者"、数值引擎充当"审查者"的系统。

这个想法在纸面上很干净。然而在实践中，从概念到一个可运行的、经过验证的解决方案的旅程充满了意想不到的障碍。

---

## 2. 网络与 API 层：与长推理模型的搏斗

### 2.1. `KeyboardInterrupt` 噩梦

**核心问题**：理论智能体使用 **DeepSeek-R1**，一种"推理"模型。与标准聊天模型在 1-5 秒内响应不同，R1 有一个内部"思考"阶段，**可持续 60 到 180 秒**。在整个窗口期间，Python `openai` 客户端保持一个打开的 HTTPS 连接，流式传输 `reasoning_content` 令牌。

在这个长窗口期间，任何网络微中断——WiFi 波动、瞬态 DNS 故障、ISP 路由变更——都会导致底层 `httpcore`/`httpx` 库引发异常，Python 的信号处理程序随后将其作为 `KeyboardInterrupt` 浮现。这不是用户按下 Ctrl+C；而是网络堆栈放弃了连接。

**发生频率**：在高峰时段，大约每 3-4 次 API 调用就会发生一次，使得系统在没有缓解措施的情况下实际上无法使用。

**解决方案：通过 `tree_log.json` 实现持久化状态**

我们实现了一个检查点系统。在每个成功验证的推导步骤之后，协调器将整个搜索树状态序列化到 `tree_log.json`。当脚本重新启动时（无论是手动还是通过包装器），它会检测到现有日志，加载最后一个检查点，并从该点重建优先级队列。

```python
# orchestrator.py — 恢复逻辑
if self.tree_log:
    last_step_key = list(self.tree_log.keys())[-1]
    last_step = self.tree_log[last_step_key]
    print(f"[Orchestrator] 从检查点恢复搜索: {last_step_key}")
    start_node = {
        "expression": last_step['to'],
        "depth": int(last_step_key.split("_")[-1]),
        "path": list(self.tree_log.values())
    }
```

**教训**：在使用长推理模型时，**状态持久化不是可选的，而是核心架构需求。** 从一开始就将管道设计为一系列幂等的、可恢复的阶段。

### 2.2. 从自由格式 LLM 输出中提取 JSON

**核心问题**：理论智能体输出一个包含 3 个提案的 JSON 数组。然而，R1 模型有时会将其 JSON 包裹在 Markdown 代码围栏中 (` ```json ... ``` `)，有时不会。更糟糕的是，早期的惰性正则 `(.*?)` 有时只会匹配 JSON 数组的*一部分*，如果模型的输出包含多个代码块或杂散括号。

**修复（多阶段提取）**：
1. **阶段 1**：尝试找到围栏代码块：`r'```(?:json)?\s*(\[.*\])\s*```'`，使用 `re.DOTALL` 和**贪婪** `(.*)`。
2. **阶段 2（后备）**：如果未找到围栏块，定位整个输出中的第一个 `[` 和最后一个 `]` 并提取该子字符串。
3. **阶段 3**：使用 `json.loads()` 解析提取的字符串。

**教训**：永远不要假设 LLM 会产生结构完美的输出。始终实现带有后备机制的分层提取策略。对于结构化数据提取，贪婪正则比惰性正则更安全。

---

## 3. 搜索策略的演进

### 3.1. 第一阶段：朴素深度优先搜索 (DFS)

初始实现是一个简单的顺序循环：向理论智能体请求一个步骤，验证它，记录它，重复。这实际上是一个分支因子为 1 的 DFS。

**问题**：这种方法没有恢复机制。如果理论智能体提出"部分分式分解"，而该路径在 5 步后走进死胡同，所有工作都白费了。系统无法回溯以尝试"积分号下微分法"。

**观察到的失败模式**：求解器经常卡在尝试从部分分式路径数值评估子积分 $\int_0^\infty \frac{x \sin(ax)}{x^2+1} dx$ 上，而这本身就是一个非平凡的积分。它会循环，提出永远无法简化的进一步分解。

### 3.2. 第二阶段：带优先级队列的最佳优先搜索 (BFS)

**决策**：我们用一个优先级队列 (`heapq`) 替换了线性循环，该队列存储*所有*已探索但未访问的节点。理论智能体现在每个节点生成 **3 条不同的路径**，协调器始终处理全局最有前途的节点，无论它属于哪个"分支"。

**优先级启发式**：$P = \text{成功概率} \times 0.9^{\text{深度}}$

该公式具有两个关键属性：
- **置信度偏好**：更高的 `success_probability`（由理论智能体估计）导致更高的优先级。
- **深度惩罚**：指数衰减 $0.9^{depth}$ 确保浅层、高置信度的路径总是在深层、投机性路径之前被探索。这防止了"无限下降"到复杂但非生产性的变换中。

**平局处理 Bug**：Python 的 `heapq` 按字典序比较元组元素。如果两个节点具有相同的优先级和深度，`heapq` 会尝试比较 `dict` 对象，引发 `TypeError`。我们通过添加一个单调递增的计数器作为元组的第三个元素来修复此问题：`(-priority, depth, self.counter, node)`。

```python
# orchestrator.py — 带平局处理的 BFS 入队
priority = prob * (0.9 ** depth)
heapq.heappush(self.queue, (-priority, depth + 1, self.counter, new_node))
self.counter += 1
```

**教训**：在任何基于 LLM 生成策略的树搜索中，具有精心设计的启发式的 BFS 显著优于 DFS。分支因子（在我们的案例中为 3）提供了找到替代路径所需的多样性，而深度惩罚防止了资源耗尽。

### 3.3. 已访问集

为了防止理论智能体提出循环变换（例如 A → B → A），我们维护一个 `visited_expressions` 集合。在处理任何节点之前，其清理后的表达式字符串会与该集合进行对照检查。如果已经被探索过，该节点会被静默丢弃。

---

## 4. 精度与验证逻辑的突破

这是整个项目中影响最大的调试挑战。即使理论智能体的数学推理完全正确，求解器也会由于有缺陷的验证逻辑而拒绝有效步骤。

### 4.1. 原始（有缺陷的）验证

初始验证很简单：数值评估父表达式和子表达式，然后检查它们在容差范围内是否相等。这对代数变换（例如因式分解、展开）有效，但**对微积分操作完全失败**。

**为什么失败**：考虑"积分号下微分法"步骤：
- **父节点**：$I(a) = \int_0^\infty \frac{\sin(ax)}{x(x^2+1)} dx \approx 0.9929$（当 $a=1$）
- **子节点**：$I'(a) = \int_0^\infty \frac{\cos(ax)}{x^2+1} dx \approx 0.5779$（当 $a=1$）

它们的数值*不相等*！子节点是父节点的*导数*。检查直接相等性会错误地剪掉这个有效且关键的步骤。

### 4.2. 修复：多模态微积分感知验证

我们重新设计了验证以尝试**多种匹配模式**，如果*任何*模式成功则接受该步骤：

```python
# orchestrator.py — 多模态验证
matches = []

# 模式 1：直接等价（用于代数变换）
p_val = self.oracle.evaluate_full_expression(self.problem, parent_expr)
c_val = self.oracle.evaluate_full_expression(self.problem, child_expr)
if p_val is not None and c_val is not None:
    matches.append(abs(p_val - c_val))

# 模式 2：父节点 ≈ d/da(子节点) — 用于"积分"步骤
if "integration" in action.lower():
    c_deriv_val = self.oracle.evaluate_derivative(self.problem, child_expr, wrt='a')
    if p_val is not None and c_deriv_val is not None:
        matches.append(abs(p_val - c_deriv_val))

# 模式 3：d/da(父节点) ≈ 子节点 — 用于"微分"步骤
if "differentiation" in action.lower():
    p_deriv_val = self.oracle.evaluate_derivative(self.problem, parent_expr, wrt='a')
    if p_deriv_val is not None and c_val is not None:
        matches.append(abs(p_deriv_val - c_val))

# 如果任何模式在容差范围内匹配则接受
if matches and min(matches) < 1e-3:
    # 步骤有效！
```

**一个微妙的陷阱**：操作类型中的"Integration"一词具有歧义性。它可以表示：
1. **反微分 (Antidifferentiation)**：$I(a) \to -\frac{\pi}{2}e^{-a} + C$（微积分步骤，模式 2 适用）。
2. **求定积分的值**：$\int_0^a \frac{\pi}{2} e^{-t} dt \to \frac{\pi}{2}(1 - e^{-a})$（代数/恒等步骤，模式 1 适用）。

多模态方法优雅地处理了这一点：如果模式 2 在情况 (2) 中失败，模式 1 仍然会成功。

### 4.3. `NumericalOracle` 鲁棒性的演进之旅

`evaluate_full_expression` 方法经历了 **5 次重大修订**：

| 版本 | 改进 | 解决的问题 |
|---|---|---|
| **v1** | 简单的 `sympy.sympify` + `.evalf()` | 基本表达式求值 |
| **v2** | 添加 `mpmath.quad` 用于数值积分 | 嵌套 `Integral()` 对象求值失败 |
| **v3** | 添加 `Eq()` 对象的 RHS 提取 | `Eq(lhs, rhs)` 表达式无法解析 |
| **v4** | 扩展命名空间（`a`, `x`, `u`, `t`, `C`），递归 `_eval_node` 函数 | 符号常数 `C` 和函数调用 `I(a)` 导致崩溃 |
| **v5（最终版）** | 奇点处理（偏移 `1e-20`），手动中心差分代替 `mp.diff` | 可去奇点（如 $\sin(x)/x$ 在 $x=0$）和导数稳定性 |

```python
# numerical_oracle.py — 手动中心差分求导
h = 1e-7
v_plus = f_val(current_val + h)
v_minus = f_val(current_val - h)
return (mp.mpf(str(v_plus)) - mp.mpf(str(v_minus))) / (2 * h)
```

**教训**：数值 Oracle 是整个系统中的**唯一信任锚点**。其他每个组件（理论智能体、编码智能体、验证智能体）都可能出错，而 Oracle 会捕获这些错误。因此，Oracle 必须是最鲁棒、最经过测试、最保守设计的组件。

---

## 5. 终端验证问题

### 5.1. 点采样快速退出 Bug

当到达终端（最终答案）节点时，编码智能体被指示在生成的 Python 脚本中插入"点采样检查"。其思路是在特定点（例如 $x = 0.999$）评估被积函数，并与 Oracle 的值进行比较。

**Bug**：传递给编码智能体的 `oracle_val` 是*整个积分的基准真值*（对于 $a=1$，≈ 0.993），**而非**被积函数在 $x = 0.999$ 处的值。编码智能体生成的脚本随后会将 $x = 0.999$ 处的被积函数值与积分值进行比较，发现巨大的偏差，并引发 `EarlyExitException` — 错误地终止了一个正确的解。

**修复**：我们停止向编码智能体传递终端节点的 `oracle_val`。Oracle 值现在仅由验证智能体用于最终残差比较，在那里它被正确地与脚本的*输出*（计算的积分值）进行比较，而非被积函数值。

```python
# orchestrator.py — 终端检查（已修复）
oracle_val = self.oracle.evaluate_ground_truth(self.problem)
implementation = self.coder.generate_implementation(self.problem, step)  # 不传 oracle_val！
# ...
verification_result = self.verifier.verify(script_path, oracle_val)  # Oracle 在这里使用
```

---

## 6. 表达式清理的雷区

### 6.1. `Eq()` 保留决策

早期版本的 `_clean_math_expr` 会剥离 `=` 号之前和包括 `=` 号在内的所有内容。这对像 `Eq(Integral(...), pi*(1-exp(-a))/2)` 这样的方程形式表达式是灾难性的，因为剥离 `Eq()` 包装器会丢失 LHS（积分）和 RHS（闭式解）之间的关系。

**决策**：我们明确保留了 `Eq()` 对象，只剥离表面标签如 `"I(a) ="` 或 `"f(x, a) ="`。

### 6.2. `I` vs `I(a)` 冲突

SymPy 使用 `I` 表示虚数单位 $\sqrt{-1}$。但我们的理论智能体经常写 `I(a)` 表示积分作为函数。我们不得不添加一个基于正则表达式的预处理器，在传递给 `sympify` 之前将 `I(` 重命名为 `IntFunc(`，同时保持独立的 `I` 作为虚数单位。

```python
# numerical_oracle.py — I(a) vs I 冲突修复
s = re.sub(r'(?<![a-zA-Z0-9_])I\(', 'IntFunc(', s)
```

---

## 7. 关键要点总结

| 类别 | 教训 | 影响 |
|---|---|---|
| **架构** | 状态持久化是长推理 AI 管道的一等需求 | 在数十次 API 故障中防止了数据丢失 |
| **搜索** | 带深度惩罚优先级的 BFS >>> DFS 用于数学探索 | 在 8 次迭代内找到了正确的推导路径 |
| **验证** | 验证必须是"微积分感知"的，而非仅仅"等式检查" | 解锁了整个积分号下微分法路径 |
| **Oracle** | 数值引擎是唯一的信任锚点；在其鲁棒性上投入最大努力 | 捕获了 100% 的无效理论智能体提案 |
| **LLM 输出** | 永远不要假设 LLM 的结构化输出；始终使用分层提取 | 消除了 JSON 截断错误 |
| **命名** | 数学符号和编程库之间的符号冲突是不可避免的 | `I(a)` vs `I`（虚数单位）是一个 2 小时的调试会话 |
| **日志** | `thinking_process.txt` 不仅仅是日志——它是外部化的工作记忆 | 对于审计理论智能体的推理不可或缺 |
