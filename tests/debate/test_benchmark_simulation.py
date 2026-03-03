"""Simulate dogfood benchmark runs to verify deterministic repair pass rate."""

import json
import pytest

from aragora.debate.output_quality import (
    apply_deterministic_quality_repairs,
    output_contract_from_dict,
    validate_output_against_contract,
)

CONTRACT_PATH = "docs/plans/dogfood_output_contract_v1.json"


@pytest.fixture
def contract():
    with open(CONTRACT_PATH) as f:
        return output_contract_from_dict(json.load(f))


# Representative outputs that mirror the 3 failure modes from the 40% benchmark.
WEAK_OUTPUT_GATE_AND_ROLLBACK = """\
## Ranked High-Level Tasks
1. **Expand placeholder/hedging patterns** — P0 Critical
2. **Extend scoring to first 5 lines** — P0 Critical
3. **Add quantitative gate criteria** — P1 High

## Suggested Subtasks
- Add regex patterns for hedging phrases (as needed, to be determined)
- Modify scoring function to evaluate first 5 lines
- Add unit tests for each new pattern

## Owner module / file paths
- Quality gate logic and pattern detection module
- Test validation and benchmarking suite

## Test Plan
- Run unit tests for each new pattern with true/false positive cases
- Run integration tests for scoring changes against sample outputs
- Benchmark suite to validate improvements reach 80% target

## Rollback Plan
We will carefully monitor the system and respond to issues as they arise
with attention to minimizing any disruption.

## Gate Criteria
- Good quality across all metrics and operational parameters
- Ensure stability and performance are maintained

## JSON Payload
```json
{"tasks": ["Expand patterns", "Extend scoring", "Add gates"]}
```
"""

WEAK_OUTPUT_ONLY_GATE = """\
## Ranked High-Level Tasks
1. **Expand hedging detection** — P0
2. **Multi-line scoring** — P0
3. **Threshold enforcement** — P1

## Suggested Subtasks
- Add 15 new regex patterns
- Implement 5-line scoring window
- Define numeric thresholds

## Owner module / file paths
- Pattern detection module in quality subsystem
- Scoring engine for actionability assessment

## Test Plan
- Test each new pattern with positive/negative cases
- Benchmark scoring against 100 sample outputs
- Run full regression suite

## Rollback Plan
If error_rate > 5% after deployment, revert the commit and restore previous
patterns. Disable the feature flag to prevent further impact.

## Gate Criteria
- Quality must be acceptable across the board
- No major regressions in existing functionality

## JSON Payload
```json
{"tasks": ["patterns", "scoring", "thresholds"]}
```
"""

GOOD_OUTPUT = """\
## Ranked High-Level Tasks
1. **Expand hedging detection** — P0 — Add 15 patterns for "as needed", TBD, etc.
2. **Score first 5 task lines** — P0 — Prevent vague lines 2-5 from passing
3. **Add threshold enforcement** — P1 — coverage >= 80%, error_rate < 1%

## Suggested Subtasks
- Add regex patterns to aragora/debate/repo_grounding.py
- Modify _score_first_batch in output_quality.py
- Add tests in tests/debate/test_output_quality.py

## Owner module / file paths
- aragora/debate/output_quality.py
- aragora/debate/repo_grounding.py
- tests/debate/test_output_quality.py

## Test Plan
- Run pytest tests/debate/test_output_quality.py (25 tests)
- Run 5 dogfood benchmarks, verify 80%+ pass rate
- Check coverage on modified files

## Rollback Plan
If error_rate > 5% after deployment, revert the commit and restore previous patterns.

## Gate Criteria
- All 25 existing tests must pass
- Coverage >= 80% on modified files
- Zero new lint errors

## JSON Payload
```json
{"test_count": 25, "coverage_target": 80}
```
"""


def _passes_after_repair(output: str, contract) -> bool:
    """Check if output passes quality gate, with deterministic repair if needed."""
    report = validate_output_against_contract(output, contract)
    if report.verdict == "good":
        return True
    repaired = apply_deterministic_quality_repairs(output, contract, report)
    repaired_report = validate_output_against_contract(repaired, contract)
    return repaired_report.verdict == "good"


def test_good_output_passes_directly(contract):
    report = validate_output_against_contract(GOOD_OUTPUT, contract)
    assert report.verdict == "good", f"Good output should pass: {report.defects}"


def test_weak_gate_and_rollback_passes_after_repair(contract):
    report = validate_output_against_contract(WEAK_OUTPUT_GATE_AND_ROLLBACK, contract)
    assert report.verdict == "needs_work", "Weak output should fail initially"

    repaired = apply_deterministic_quality_repairs(WEAK_OUTPUT_GATE_AND_ROLLBACK, contract, report)
    repaired_report = validate_output_against_contract(repaired, contract)
    assert repaired_report.verdict == "good", f"Should pass after repair: {repaired_report.defects}"


def test_weak_gate_only_passes_after_repair(contract):
    report = validate_output_against_contract(WEAK_OUTPUT_ONLY_GATE, contract)
    # This one has a good rollback (trigger + action) but bad gate criteria
    repaired = apply_deterministic_quality_repairs(WEAK_OUTPUT_ONLY_GATE, contract, report)
    repaired_report = validate_output_against_contract(repaired, contract)
    assert repaired_report.verdict == "good", f"Should pass after repair: {repaired_report.defects}"


def test_benchmark_simulation_80_percent_pass_rate(contract):
    """Simulate 5 benchmark runs and verify >= 80% pass after repair."""
    outputs = [
        WEAK_OUTPUT_GATE_AND_ROLLBACK,
        GOOD_OUTPUT,
        GOOD_OUTPUT,  # Good runs tend to cluster
        WEAK_OUTPUT_ONLY_GATE,
        WEAK_OUTPUT_GATE_AND_ROLLBACK,
    ]
    passed = sum(1 for out in outputs if _passes_after_repair(out, contract))
    assert passed >= 4, f"Expected >= 80% pass rate, got {passed}/5 ({100 * passed // 5}%)"
