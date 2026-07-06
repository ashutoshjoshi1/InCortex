# InCortex Mathematical Model

This document defines the quantitative rules behind every layer of InCortex — the same way a neural network is defined by its equations, not just its diagram. Every score, threshold, and update rule that appears in [Design_Doc.md](../Design_Doc.md) is formalized here so that implementation (and tests) can verify exact behavior.

**How to read this doc:** each layer gets a section with numbered equations. Section 10 maps every planned source file to the equations it must implement. All tunable weights and thresholds are configuration values (Design_Doc §24) — the numbers given here are recommended defaults, not hard-coded constants.

---

## 0. Notation

| Symbol | Meaning |
| ------ | ------- |
| $x$ | input (message payload, possibly a vector) |
| $y$ | output of a Cell/Tissue/Organ |
| $m$ | a `CortexMessage` |
| $\mathbf{e}_x \in \mathbb{R}^d$ | embedding vector of $x$ |
| $c \in [0,1]$ | confidence score |
| $h \in [0,1]$ | health score |
| $s \in \{0,1\}$ | task success indicator |
| $t$ | time (timestamps in seconds unless noted) |
| $\alpha$ | EMA smoothing rate |
| $\lambda$ | exponential decay rate |
| $\eta$ | learning rate |
| $\tau_\bullet$ | a threshold (subscript names it) |
| $w_i$ | mixing weights, always normalized so $\sum_i w_i = 1$ |

Convention: **every score in InCortex is normalized to $[0,1]$** before it crosses a component boundary. This makes scores from different Cells, Organs, and layers directly comparable and composable.

---

## 1. Cell Mathematics

A biological neuron computes a weighted sum and fires through an activation:

$$
y = \varphi\Big(\sum_i w_i x_i + b\Big) \tag{1.1}
$$

InCortex generalizes the neuron. A **Cell** is a function that takes a message and memory context and returns an output *with a confidence*:

$$
C : (m, \mathcal{M}) \mapsto (y, c) \tag{1.2}
$$

### 1.1 Activation

For Cells with trainable internals (classifier-style Cells such as `IntentCell`), the neuron form applies directly, with standard activations:

$$
\text{sigmoid}(z) = \frac{1}{1+e^{-z}}, \qquad
\text{softmax}(z)_k = \frac{e^{z_k}}{\sum_j e^{z_j}} \tag{1.3}
$$

For Cells that wrap an LLM or rule engine, "activation" is the wrapped call; the math contract is only about the *scores* it must emit (below).

### 1.2 Confidence

Every Cell must emit $c \in [0,1]$ with its output.

**Classifier-style Cells** (a distribution $p$ over $K$ options) use normalized-entropy confidence:

$$
c = 1 - \frac{H(p)}{\log K}, \qquad H(p) = -\sum_{k=1}^{K} p_k \log p_k \tag{1.4}
$$

Interpretation: $c = 1$ when one option gets all probability; $c = 0$ when the Cell is maximally unsure (uniform). A simpler substitute is $c = \max_k p_k$, but (1.4) is preferred because it uses the whole distribution.

**History-calibrated confidence.** Raw per-call confidence is blended with the Cell's track record — a Beta-Bernoulli estimate with Laplace smoothing (the "rule of succession"):

$$
\hat{c}_{\text{hist}} = \frac{k + 1}{n + 2} \tag{1.5}
$$

where $k$ = successful outputs and $n$ = total outputs in the evaluation window. The reported confidence is:

$$
c_{\text{final}} = \gamma \, c_{\text{raw}} + (1-\gamma)\, \hat{c}_{\text{hist}}, \qquad \gamma = 0.7 \text{ (default)} \tag{1.6}
$$

A brand-new Cell ($n=0$) therefore reports $\hat{c}_{\text{hist}} = 0.5$ — honest uncertainty, not false confidence.

### 1.3 Health

Health blends success rate, confidence, and latency, each tracked as an exponential moving average:

$$
\bar{v}_t = (1-\alpha)\,\bar{v}_{t-1} + \alpha\, v_t, \qquad \alpha = 0.1 \text{ (default)} \tag{1.7}
$$

$$
h = w_s\,\bar{s} + w_c\,\bar{c} + w_\tau \Big(1 - \min\big(1, \tfrac{\bar{\tau}}{\tau_{\max}}\big)\Big),
\qquad (w_s, w_c, w_\tau) = (0.5,\ 0.3,\ 0.2) \tag{1.8}
$$

where $\bar{s}$ = EMA of success, $\bar{c}$ = EMA of confidence, $\bar{\tau}$ = EMA of latency, $\tau_{\max}$ = latency budget. Health maps to the status reported by `health_check()`:

$$
\text{status} =
\begin{cases}
\text{active} & h \geq 0.7 \\
\text{degraded} & 0.4 \leq h < 0.7 \\
\text{failing} & h < 0.4
\end{cases} \tag{1.9}
$$

### 1.4 Cell Learning Hook

For Cells with trainable parameters $\theta$, learning is gradient descent on a loss $L$:

$$
\theta \leftarrow \theta - \eta \nabla_\theta L \tag{1.10}
$$

For non-trainable Cells (LLM-wrapping or rule-based), `learn(feedback)` updates the *statistics* instead: the success counter $k, n$ in (1.5), the EMAs in (1.7), and strategy values in §6.3. Either way, feedback must move future numbers.

---

## 2. Tissue Mathematics

A Tissue combines the outputs of its Cells. Combination is **confidence-weighted**, via a temperature-controlled softmax:

$$
w_i = \frac{e^{c_i / T}}{\sum_j e^{c_j / T}} \tag{2.1}
$$

- $T \to 0$: winner-take-all (trust only the most confident Cell)
- $T \to \infty$: uniform average (ignore confidence)
- Default $T = 0.5$

**Numeric outputs** combine as a weighted sum; **categorical outputs** (e.g., competing intent labels) combine by weighted vote:

$$
y_T = \sum_i w_i\, y_i
\qquad\text{or}\qquad
y_T = \arg\max_k \sum_i w_i \,\mathbb{1}[y_i = k] \tag{2.2}
$$

**Selective routing (mixture-of-experts).** When a Tissue should not run every Cell, a gate scores each Cell against the input and only the top-$k$ fire:

$$
g(x) = \text{softmax}(W_g\, \mathbf{e}_x), \qquad \text{run Cells in } \text{top-}k\big(g(x)\big) \tag{2.3}
$$

**Tissue confidence and health.** Tissue confidence is the weighted mean of member confidences using (2.1); Tissue health is deliberately conservative — a Tissue is only as healthy as its weakest critical Cell:

$$
c_T = \sum_i w_i c_i, \qquad
h_T = \min\Big(\underset{i}{\text{mean}}\, h_i,\ \min_{i \in \text{critical}} h_i\Big) \tag{2.4}
$$

---

## 3. Organ Mathematics

An Organ runs an internal pipeline of Tissues/Cells (stage $1 \to n$).

**Pipeline confidence.** Confidence must *degrade* through a chain — a conclusion built on shaky steps is shaky. Use the geometric mean (default) or the minimum (conservative mode for safety-relevant Organs):

$$
c_O = \Big(\prod_{i=1}^{n} c_i\Big)^{1/n}
\qquad\text{or}\qquad
c_O = \min_i c_i \tag{3.1}
$$

The geometric mean punishes any single low-confidence stage far more than an arithmetic mean would — e.g. stages $(0.9, 0.9, 0.2)$ give $c_O = 0.54$, not $0.67$.

**Organ relevance** (used by the Router, §4): each Organ maintains an embedding $\mathbf{e}_O$ of its capability description; relevance to message $m$ is cosine similarity:

$$
r_O(m) = \cos(\mathbf{e}_m, \mathbf{e}_O) = \frac{\mathbf{e}_m \cdot \mathbf{e}_O}{\lVert\mathbf{e}_m\rVert\, \lVert\mathbf{e}_O\rVert} \tag{3.2}
$$

**Organ health** aggregates member Tissue healths with (2.4) applied recursively.

---

## 4. Cortex Core Mathematics

### 4.1 The Cognitive Loop as Function Composition

The loop *Listen → Understand → Remember → Reason → Plan → Act → Speak → Learn* is a composition — each stage feeds the next, and Learn closes the loop by updating state for the future:

$$
y = (\text{Speak} \circ \text{Act} \circ \text{Plan} \circ \text{Reason} \circ \text{Remember} \circ \text{Understand})(x) \tag{4.1}
$$

### 4.2 Routing

Given intent distribution $p(\text{intent} \mid m)$ from the Language Organ and relevance scores (3.2), the Router selects the Organ set:

$$
\mathcal{O}^\ast = \{\, O : r_O(m) \geq \tau_{\text{route}} \,\}, \qquad \tau_{\text{route}} = 0.35 \text{ (default)} \tag{4.2}
$$

with fallback $\mathcal{O}^\ast = \{\arg\max_O r_O(m)\}$ if the set is empty (something must always handle the message).

### 4.3 Scheduling Priority

Every queued task gets a priority score; the scheduler always pops the max. The age term guarantees no task starves:

$$
P = w_u\, u + w_i\, i + w_a \min\Big(1, \frac{\text{age}}{\text{age}_{\max}}\Big),
\qquad (w_u, w_i, w_a) = (0.5,\ 0.3,\ 0.2) \tag{4.3}
$$

where $u \in [0,1]$ is urgency (from the message `priority` field), $i \in [0,1]$ is importance, and age is time spent queued.

### 4.4 Answer Acceptance

The Cortex only emits an answer whose end-to-end confidence (3.1, composed across the Organs used) clears a floor; otherwise it asks for clarification:

$$
\text{emit if } c_{\text{final}} \geq \tau_{\text{answer}}, \qquad \tau_{\text{answer}} = 0.4 \text{ (default)} \tag{4.4}
$$

---

## 5. Memory Mathematics

### 5.1 Embedding and Similarity

Every memory record $r$ stores an embedding $\mathbf{e}_r = E(\text{content})$. Similarity between a query $q$ and a record is cosine similarity (3.2), rescaled from $[-1,1]$ to $[0,1]$:

$$
\text{sim}(q, r) = \tfrac{1}{2}\big(1 + \cos(\mathbf{e}_q, \mathbf{e}_r)\big) \tag{5.1}
$$

### 5.2 Recency — the Forgetting Curve

Memory strength decays exponentially, exactly like the Ebbinghaus forgetting curve:

$$
\text{rec}(r, t) = e^{-\lambda (t - t_r)}, \qquad \lambda = \frac{\ln 2}{t_{1/2}} \tag{5.2}
$$

where $t_r$ is the record's last-access time and $t_{1/2}$ is the half-life (default: 7 days for short-term relevance; long-term memories use a longer half-life or $\lambda = 0$). **Accessing a memory resets $t_r$** — recall strengthens retention, as in biology.

### 5.3 Importance Score

Design_Doc §15.4 lists seven scoring factors. Their formal combination:

$$
I_r = w_1\,\text{rel} + w_2\,\text{freq} + w_3\,\text{conf}_{\text{user}} + w_4\,\text{impact} + w_5\,\text{rec} + w_6\,c_r + w_7\,\text{uniq} \tag{5.3}
$$

with defaults $(w_1,\dots,w_7) = (0.25,\ 0.15,\ 0.15,\ 0.15,\ 0.10,\ 0.10,\ 0.10)$ and each factor in $[0,1]$:

- **rel** — relevance to active goals: max similarity (5.1) against goal embeddings
- **freq** — log-normalized access count: $\text{freq} = \dfrac{\log(1 + n_r)}{\log(1 + n_{\max})}$
- **conf**$_{\text{user}}$ — 1 if the user explicitly confirmed the fact, else 0
- **impact** — mean learning score (6.2) of tasks that used this memory
- **rec** — recency (5.2)
- $c_r$ — confidence the memory is correct
- **uniq** — novelty: $\text{uniq} = 1 - \max_{r' \neq r} \text{sim}(r, r')$ (near-duplicates score low)

### 5.4 Retrieval Score

What actually gets retrieved for a query balances similarity, recency, and importance (the classic retrieval triad):

$$
S(q, r) = \beta_1\, \text{sim}(q,r) + \beta_2\, \text{rec}(r,t) + \beta_3\, I_r,
\qquad (\beta_1,\beta_2,\beta_3) = (0.6,\ 0.2,\ 0.2) \tag{5.4}
$$

Retrieve $\text{top-}k$ records by $S$, subject to $S \geq \tau_{\text{retrieve}}$ (default $0.25$) so irrelevant memories are never injected just to fill $k$ slots.

### 5.5 Forgetting, Compression, and Budget

Memory must not grow endlessly. Each record has a retention value; when it drops below the floor, the record is summarized/compressed or archived (never silently deleted — Design_Doc §25.3):

$$
R_r(t) = I_r \cdot e^{-\lambda (t - t_r)}, \qquad
R_r(t) < \tau_{\text{forget}} \Rightarrow \text{compress or archive} \tag{5.5}
$$

Under a store-size budget $B$, cleanup keeps the top-$B$ records by $R_r(t)$ and compresses the tail.

### 5.6 Working Memory Selection

Working memory is a token-budgeted knapsack: choose the record set $\mathcal{R}$ maximizing total retrieval score within the context budget $B_{\text{tok}}$:

$$
\max_{\mathcal{R}} \sum_{r \in \mathcal{R}} S(q, r) \quad \text{s.t.} \sum_{r \in \mathcal{R}} \text{tokens}(r) \leq B_{\text{tok}} \tag{5.6}
$$

Greedy by $S(q,r) / \text{tokens}(r)$ (value density) is the accepted approximation.

---

## 6. Learning Mathematics

### 6.1 Feedback Normalization

User ratings on any scale normalize to $[0,1]$:

$$
\hat{r} = \frac{r - r_{\min}}{r_{\max} - r_{\min}} \tag{6.1}
$$

### 6.2 Learning Score per Task

Design_Doc §16.3's high/medium/low bands become a continuous score:

$$
L = \text{clip}_{[0,1]}\Big( w_s\, s + w_r\, \hat{r} - w_c\, \text{corr} - w_p\, \text{pen} \Big),
\qquad (w_s, w_r, w_c, w_p) = (0.4,\ 0.4,\ 0.3,\ 0.3) \tag{6.2}
$$

where $s$ = task success, $\hat{r}$ = normalized rating, corr $\in [0,1]$ = correction severity (0 none, 1 total rewrite), pen = 1 if a tool failed or an unsafe action was attempted. Bands: $L \geq 0.7$ high, $0.4$–$0.7$ medium, $< 0.4$ low.

### 6.3 Strategy Value Updates (Bandit Learning)

When InCortex can choose between strategies (prompt styles, reasoning modes, retrieval settings), each strategy $a$ keeps a running value updated after every use — the standard incremental value estimate:

$$
Q_{t+1}(a) = Q_t(a) + \eta\,\big(L_t - Q_t(a)\big), \qquad \eta = 0.1 \tag{6.3}
$$

Strategy *selection* balances exploitation and exploration with UCB:

$$
a^\ast = \arg\max_a \left[ Q(a) + \kappa \sqrt{\frac{\ln N}{n_a}} \right], \qquad \kappa = 1.0 \tag{6.4}
$$

where $N$ = total trials, $n_a$ = trials of strategy $a$. Untried strategies ($n_a = 0$) are tried first.

### 6.4 Mistake Tracking

Mistakes are clustered by embedding similarity (5.1) with cluster threshold $\tau_{\text{mistake}} = 0.85$. For each cluster $M$, track the repeat rate over a sliding window and the trend:

$$
\text{repeat}(M) = \frac{n_M^{\text{window}}}{n^{\text{window}}}, \qquad
\Delta E = \bar{E}_{\text{recent}} - \bar{E}_{\text{previous}} \tag{6.5}
$$

$\Delta E < 0$ means the system is genuinely improving; a cluster with rising repeat rate is escalated into memory as an explicit "known weakness" record with high importance.

### 6.5 Skill Promotion

A recurring successful pattern is promoted to a reusable skill when it has both enough evidence and a high enough success rate — using the smoothed estimate (1.5) so small samples can't sneak through:

$$
\text{promote if } n \geq N_{\min} \text{ and } \frac{k+1}{n+2} \geq \tau_{\text{skill}},
\qquad N_{\min} = 5,\ \tau_{\text{skill}} = 0.8 \tag{6.6}
$$

### 6.6 Self-Evaluation Calibration (v0.4+)

A self-scoring system must be *calibrated*: when it says 80% confident, it should be right about 80% of the time. Two standard measures, tracked as metrics:

$$
\text{Brier} = \frac{1}{n} \sum_{i=1}^{n} (c_i - o_i)^2, \qquad
\text{ECE} = \sum_{b=1}^{B} \frac{n_b}{n}\, \big|\,\text{acc}(b) - \text{conf}(b)\,\big| \tag{6.7}
$$

where $o_i \in \{0,1\}$ is the actual outcome and bins $b$ group predictions by confidence. Lower is better; Brier $= 0.25$ is the "always say 0.5" baseline to beat.

### 6.7 Later Phases (v1.0+, reference only)

Fine-tuning minimizes cross-entropy $L = -\sum_i \log p_\theta(y_i \mid x_i)$; reinforcement learning maximizes expected reward $J(\theta) = \mathbb{E}_{\pi_\theta}[R]$ via policy gradient. These enter at v1.0/v1.5 (see ROADMAP) and will get their own detailed spec before implementation.

---

## 7. Safety Mathematics

### 7.1 Risk Score

Classic risk = likelihood × impact, both estimated on $[0,1]$:

$$
R = p(\text{harm}) \times \text{impact} \tag{7.1}
$$

### 7.2 The Permission Gate

An action $a$ with permission level $\ell(a) \in \{0,\dots,5\}$ executes only if **both** the level check and the risk check pass:

$$
\text{allow}(a) =
\begin{cases}
\text{execute} & \ell(a) \leq L_{\max} \ \wedge\ R(a) < \tau_{\text{risk}} \\
\text{require human approval} & \ell(a) \geq 4 \ \vee\ R(a) \geq \tau_{\text{risk}} \\
\text{block} & \ell(a) > L_{\max}
\end{cases} \tag{7.2}
$$

with $\tau_{\text{risk}} = 0.3$ and $L_{\max}$ from config (default 2). This is a **fail-closed** gate: any error while computing $R$ or $\ell$ is treated as $R = 1$.

### 7.3 Anomaly Flagging

Behavioral metrics (action rate, tool-call volume, memory-write volume) are monitored with z-scores; anything beyond $3\sigma$ triggers review:

$$
z = \frac{x - \mu}{\sigma}, \qquad |z| > 3 \Rightarrow \text{flag} \tag{7.3}
$$

---

## 8. System Metrics Mathematics

The metrics from Design_Doc §27, defined precisely:

$$
\text{success rate} = \frac{\#\{\text{tasks with } L \geq 0.7\}}{\#\text{tasks}} \tag{8.1}
$$

**Memory retrieval accuracy** (needs labeled relevance, gathered from feedback):

$$
\text{P@}k = \frac{|\text{relevant} \cap \text{top-}k|}{k}, \qquad
\text{R@}k = \frac{|\text{relevant} \cap \text{top-}k|}{|\text{relevant}|}, \qquad
\text{MRR} = \frac{1}{n}\sum_i \frac{1}{\text{rank}_i} \tag{8.2}
$$

**Latency** is reported as percentiles ($p50 / p95 / p99$), never means — tail latency is what users feel. **Improvement over time** is the learning-score trend, EMA-smoothed with (1.7):

$$
\text{improvement} = \bar{L}_{\text{this week}} - \bar{L}_{\text{last week}} \tag{8.3}
$$

System-wide health is the recursive aggregation: Cells (1.8) → Tissues (2.4) → Organs (§3) → Brain.

---

## 9. Worked Example — One Message Through the Math

User asks: *"Explain neural networks"* (having previously said they like simple explanations).

1. **IntentCell** classifies: $p = (\text{explain: } 0.85,\ \text{chat: } 0.10,\ \text{other: } 0.05)$ → entropy confidence (1.4): $c = 1 - \frac{0.52}{\log 3} = 0.53$; blended with history (1.6, $\hat{c}_{\text{hist}} = 0.9$): $c_{\text{final}} = 0.7 \cdot 0.53 + 0.3 \cdot 0.9 = 0.64$.
2. **Router** (4.2): $r_{\text{Language}} = 0.82$, $r_{\text{Memory}} = 0.61$, $r_{\text{Reasoning}} = 0.44$, all $\geq 0.35$ → all three Organs selected.
3. **Memory retrieval** (5.4): the record *"user prefers simple explanations"* scores $S = 0.6(0.71) + 0.2(0.94) + 0.2(0.80) = 0.77$ → retrieved; its $t_r$ resets (5.2).
4. **Pipeline confidence** (3.1): stages $(0.64, 0.77, 0.81)$ → $c_O = (0.64 \cdot 0.77 \cdot 0.81)^{1/3} = 0.74 \geq \tau_{\text{answer}}$ → answer emitted in simple English.
5. **Feedback**: user thumbs-up → $s = 1$, $\hat{r} = 1$, no correction → $L = \text{clip}(0.4 + 0.4) = 0.8$ (6.2) → high band; the memory's **impact** factor rises (5.3), the strategy "simple-English response" gets $Q \mathrel{+}= 0.1(0.8 - Q)$ (6.3), and IntentCell's success counter increments (1.5).

Every arrow in the cognitive loop moved a number. That is the design goal.

---

## 10. File-to-Math Map

Every planned module and the equations it must implement:

| File | Equations | What it computes |
| ---- | --------- | ---------------- |
| `core/cortex.py` | 4.1, 4.4, 3.1 | loop composition, answer acceptance |
| `core/router.py` | 3.2, 4.2 | organ relevance, routing set |
| `core/scheduler.py` | 4.3 | priority scoring, starvation-free queue |
| `core/message.py` | §0 convention | normalized confidence field propagation |
| `core/state.py` | 1.7 | EMA-smoothed system statistics |
| `core/config.py` | all defaults | weights, thresholds, half-lives from YAML |
| `cells/base_cell.py` | 1.2, 1.5–1.9 | confidence blend, health, status bands |
| `cells/text_cell.py` | 1.4 | output confidence |
| `cells/intent_cell.py` | 1.3, 1.4 | softmax over intents, entropy confidence |
| `cells/memory_cell.py` | 5.1, 5.4 | retrieval scoring |
| `cells/reasoning_cell.py` | 3.1 | per-step confidence, chain degradation |
| `cells/planner_cell.py` | 4.3, 7.1 | step priority, plan risk estimate |
| `cells/feedback_cell.py` | 6.1, 6.2 | rating normalization, learning score |
| `cells/safety_cell.py` | 7.1, 7.2 | risk score, gate decision |
| `tissues/base_tissue.py` | 2.1, 2.2, 2.4 | weighted combine, tissue health |
| `tissues/language_tissue.py` | 2.1–2.3 | gated cell selection |
| `tissues/memory_tissue.py` | 2.2, 5.4 | merged retrieval across memory cells |
| `tissues/reasoning_tissue.py` | 2.1, 3.1 | mode selection, chain confidence |
| `tissues/learning_tissue.py` | 6.2, 6.3 | score aggregation, strategy values |
| `organs/base_organ.py` | 3.1, 3.2, 2.4 | pipeline confidence, relevance, health |
| `organs/memory_organ.py` | 5.1–5.6 | full memory math |
| `organs/reasoning_organ.py` | 3.1 (min mode) | conservative confidence |
| `organs/planning_organ.py` | 4.3, 7.1 | plan scoring and risk |
| `organs/learning_organ.py` | 6.1–6.6 | full learning math |
| `organs/safety_organ.py` | 7.1–7.3 | risk, gate, anomaly detection |
| `memory/memory_record.py` | 5.3 | importance factors as fields |
| `memory/short_term.py` | 5.2, 5.6 | fast decay, working-memory knapsack |
| `memory/long_term.py` | 5.3, 5.5 | importance, retention, compression |
| `memory/vector_memory.py` | 5.1 | embedding similarity search |
| `memory/episodic_memory.py` | 5.2, 5.4 | time-weighted episode retrieval |
| `memory/memory_manager.py` | 5.4, 5.5 | retrieval orchestration, budget cleanup |
| `learning/feedback.py` | 6.1 | normalization |
| `learning/evaluator.py` | 6.2, 6.7 | learning score, calibration |
| `learning/learning_loop.py` | 6.3, 6.4 | value updates, UCB selection |
| `learning/mistake_tracker.py` | 6.5, 5.1 | mistake clustering, repeat/trend |
| `learning/skill_builder.py` | 6.6 | promotion rule |
| `safety/permissions.py` | 7.2 | level check |
| `safety/risk.py` | 7.1 | likelihood × impact |
| `safety/policy.py` | 7.2 | fail-closed gate |
| `safety/approval.py` | 7.2 (middle case) | approval routing |
| `tools/tool_registry.py` | 7.1 | per-tool risk levels |
| `tools/base_tool.py` | 7.2 | gate enforcement before execute |
| `api/routes_*.py` | 8.1–8.3 | metrics exposure (`/v1/health`, `/v1/logs`) |
| `tests/*` | all | property tests, §11 below |

---

## 11. Testing the Math

Each equation carries testable properties — these become unit tests before any tuning:

1. **Range**: every score function returns values in $[0,1]$ for all valid inputs.
2. **Monotonicity**: health (1.8) never rises when error rate rises; retrieval score (5.4) never falls when similarity rises; risk gate (7.2) never *loosens* as $R$ grows.
3. **Limits**: (2.1) approaches winner-take-all as $T \to 0$ and uniform as $T \to \infty$; (1.5) → 0.5 with no data.
4. **Decay**: (5.2) halves exactly every $t_{1/2}$; accessed memories outlive untouched ones.
5. **Degradation**: pipeline confidence (3.1) is never higher than its weakest stage under min mode, and never higher than its arithmetic mean under geometric mode.
6. **Fail-closed**: any exception inside risk computation yields the block/approval branch of (7.2), never execute.
7. **Convergence**: (6.3) converges to the true mean reward of a stationary strategy.
8. **Starvation-freedom**: under (4.3), every queued task's priority eventually exceeds any fixed bound as age grows.
