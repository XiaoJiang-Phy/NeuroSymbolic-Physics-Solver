# 凝聚态物理扩展蓝图 (CMP Expansion Roadmap)

本路线图旨在将 **NeuroSymbolic Physics Solver** 从通用的数学求解器演进为专业级的“凝聚态物理 AI 研究员”。核心目标是将 `Theorist` 的原子推理步骤扩展到算符代数和多体物理领域，并引入物理一致性审计机制。

---

## 📅 阶段 1：算符与矩阵代数核心 (Symbolic Physics Core)
**目标**：使系统具备处理量子力学基本算符和矩阵变换的能力。

*   **1.1 [ ] 算符代数引擎 (Commutator Algebra)**
    *   支持对易子 $[A, B]$ 和反对易子 $\{A, B\}$ 的化简。
    *   引入符号化的二次量子化算符（费米子/玻色子 $c_k, c_k^\dagger$）。
*   **1.2 [ ] 矩阵力学与有效模型**
    *   支持 Pauli 矩阵、Spinor 基底的符号变换。
    *   实现有效哈密顿量的低能级差变换（如 Schrieffer-Wolff 变换）的原子步化推导。
*   **1.3 [ ] 物理单位感知 (Unit Engineering)**
    *   在推导中强制保留物理常数（$\hbar, k_B, e, m_e$）。
    *   集成 `unit_eng` 技能进行自动量纲分析。

---

## 📅 阶段 2：物理一致性审计 (Physics Audit & Constraints)
**目标**：建立“物理红线”检查机制，确保推导结果在物理上是自洽的。

*   **2.1 [ ] 守恒律审计 (Conservation Laws)**
    *   检查每步变换是否满足电荷、能量、动量和粒子数守恒。
*   **2.2 [ ] 性质正定性与解析性 (Analytic Properties)**
    *   验证光谱函数 $A(\mathbf{k}, \omega)$ 的正定性。
    *   检查 Green 函数在复平面上的解析性（因果律约束 $i\eta$）。
*   **2.3 [ ] 自动求和规则校验 (Sum Rules)**
    *   利用 $f$-sum rule 等经典求和规则进行数值校验。
*   **2.4 [ ] 物理决策日志 (Physics Audit Log)**
    *   使用 `physics_audit` 记录每一步物理决策的逻辑背景。

---

## 📅 阶段 3：多体物理专项引擎 (Many-Body Physics Engines)
**目标**：解决凝聚态物理中最具挑战性的有限温和强关联问题。

*   **3.1 [ ] Matsubara 频率转换引擎**
    *   实现从离散 Matsubara 求和到连续频率轴解析延拓（Analytic Continuation）的推导。
*   **3.2 [ ] 费曼图翻译器 (Diagrammatic Reasoning)**
    *   将费曼图规则（Feynman Rules）转化为具体的符号积分。
    *   自动处理自能（Self-energy）和自洽 Gap 方程。
*   **3.3 [ ] 重正化群 (RG) 算子**
    *   引入尺度变换规则，支持耦合常数流（Flow equations）的推导。

---

## 📅 阶段 4：拓扑、输运与可视化 (Topology & Visualization)
**目标**：覆盖现代凝聚态前沿，并生成出版级的科研产出。

*   **4.1 [ ] 拓扑不变量自动计算**
    *   实现从 $H(\mathbf{k})$ 到 Berry 曲率再到 Chern Number 的自动化积分管道。
*   **4.2 [ ] 线性响应与输运理论**
    *   自动派生电导、热导、Hall 系数等 Kubo 公式表达式。
*   **4.3 [ ] 出版级物理制图 (Scientific Plotting)**
    *   集成 `sci_plot` 技能，输出符合 APS/Nature 标准的能带图、态密度图。

---

## 🧪 首个验证任务 (Prototype Task)
**一维紧束缚模型的格林函数与态密度推导**
1.  **输入**：$H = -t \sum \langle i,j \rangle c_i^\dagger c_j$。
2.  **原子步**：实空间 $\rightarrow$ $k$-空间 $\rightarrow$ 频率空间 $\rightarrow$ 解析延拓 $\rightarrow$ 取虚部得到 DOS。
3.  **验证**：利用 `Verifier` 检查 DOS 在全带宽范围内的积分为 1。

---

> [!NOTE]  
> 本路线图是动态演进的，所有物理决策逻辑应当被持久化记录于 `DECISION_LOG.md`。
