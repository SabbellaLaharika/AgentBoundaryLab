import os
import json
import re
import pytest

SANDBOX_NAME_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")

def test_reliability_report_and_math():
    report_path = os.path.join("reports", "reliability.json")
    assert os.path.exists(report_path), f"Missing {report_path}"

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    run_count = data.get("run_count")
    assert isinstance(run_count, int)
    assert run_count >= 20, f"run_count must be >= 20, got {run_count}"

    runs = data.get("runs", [])
    assert len(runs) == run_count, f"runs list length {len(runs)} must equal run_count {run_count}"

    sandbox_names = []
    wall_clocks = []
    boot_times = []
    cost_total = 0.0
    successes = 0

    for idx, r in enumerate(runs):
        assert "sandbox_name" in r, f"Run {idx} missing sandbox_name"
        name = r["sandbox_name"]
        assert SANDBOX_NAME_REGEX.match(name), f"Run {idx} invalid sandbox_name '{name}'"
        sandbox_names.append(name)

        assert r.get("fresh") is True, f"Run {idx} fresh must be True"
        assert isinstance(r.get("success"), bool), f"Run {idx} success must be boolean"
        if r["success"]:
            successes += 1

        wc = r.get("wall_clock_s")
        assert isinstance(wc, (int, float)) and wc > 0
        wall_clocks.append(wc)

        boot = r.get("boot_to_ready_s")
        assert isinstance(boot, (int, float)) and boot > 0
        boot_times.append(boot)

        cost = r.get("cost_usd")
        assert isinstance(cost, (int, float)) and cost >= 0
        cost_total += cost

    # Names must be unique
    assert len(sandbox_names) == len(set(sandbox_names)), "All sandbox_names in runs must be unique"

    # Wall clock must be sorted ascending
    assert wall_clocks == sorted(wall_clocks), "wall_clock_s in runs must be sorted ascending"

    # Success rate
    expected_success_rate = round(successes / float(run_count), 4)
    assert abs(data.get("success_rate", 0) - expected_success_rate) < 0.001

    # Exact median check for 20 items (mean of 10th and 11th, 1-based, index 9 and 10)
    expected_median_wc = round((wall_clocks[9] + wall_clocks[10]) / 2.0, 4)
    assert abs(data.get("median_wall_clock_s", 0) - expected_median_wc) < 0.001

    # Exact p90 check (18th item, 1-based, index 17)
    expected_p90_wc = round(wall_clocks[17], 4)
    assert abs(data.get("p90_wall_clock_s", 0) - expected_p90_wc) < 0.001

    # Boot-to-ready median
    sorted_boot = sorted(boot_times)
    expected_median_boot = round((sorted_boot[9] + sorted_boot[10]) / 2.0, 4)
    assert abs(data.get("median_boot_to_ready_s", 0) - expected_median_boot) < 0.001

    # Total cost sum check
    assert abs(data.get("total_cost_usd", 0) - cost_total) < 0.01

    # Postmortem path verification
    postmortem_path = data.get("postmortem_path", "")
    assert postmortem_path == "reports/postmortem.md"
    norm_pm_path = postmortem_path.replace("/", os.sep)
    assert os.path.exists(norm_pm_path), f"Postmortem file missing: {norm_pm_path}"

    with open(norm_pm_path, "r", encoding="utf-8") as f:
        pm_content = f.read()

    assert len(pm_content) >= 200, f"Postmortem content must be >= 200 chars, got {len(pm_content)}"
