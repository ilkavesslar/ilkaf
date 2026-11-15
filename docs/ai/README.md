# AI & Machine Learning Architecture (docs/ai)

## 1. Role of AI in ILKA

In the ILKA platform, Artificial Intelligence (AI) operates above the low-level computer vision detector layer to perform:
- **Temporal Event Aggregation**: Evaluating sequences of vision frames to distinguish fleeting anomalies from genuine sustained hazards.
- **Incident Severity Scoring**: Calculating multi-factor risk scores based on zone criticality, duration, and worker proximity.
- **Predictive Near-Miss Analytics**: Identifying recurring micro-breaches to highlight dangerous operational bottlenecks before injury occurs.
- **Explainability & Model Transparency**: Generating interpretable feature attributions and confidence diagnostics.

---

## 2. Core Mandate: Probabilistic Observation

> [!IMPORTANT]
> **Probabilistic Principle**: All AI models generate **probabilistic observations**, not deterministic facts. No AI model is 100% accurate.

Consequently, every AI output emitted to the event bus must strictly conform to a standardized schema containing:
1. **Timestamp**: UTC ISO 8601 timestamp of analysis.
2. **Source Identifier**: Camera ID, Edge Node ID, and Spatial Zone ID.
3. **Detection / Event Classification**: Specific hazard class (e.g., `PPE_VIOLATION_VIB_VEST`, `ZONE_INCURSION_ROBOTIC_CELL`).
4. **Confidence Score**: Normalized probability float `[0.0, 1.0]`.
5. **Model Identity**: Unique model slug (e.g., `ilka-temporal-risk-v1`).
6. **Model Version**: Semantic version and training checkpoint hash.
7. **Spatial Metadata**: Bounding polygon, coordinates, and normalized bounding box.

---

## 3. Human-in-the-Loop (HITL) Verification

To prevent false alarms from disrupting plant operations and to guarantee safety-critical accountability:
- Automated AI scoring triggers **Candidate Incidents**.
- Candidate incidents are dispatched to the operations dashboard.
- A human operator or safety supervisor must review the synchronized snapshot/clip and either **Verify** (confirming true positive) or **Dismiss** (flagging false positive with reason).
- Verified incidents enter the compliance record and trigger escalation protocols.
- Operator feedback is stored to evaluate model precision and drift over time.
