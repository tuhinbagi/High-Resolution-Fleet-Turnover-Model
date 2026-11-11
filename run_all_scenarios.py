"""Run every survival-curve x EV-scenario combination reported in the paper."""
from High_Resolution_Fleet_Turnover_Model import main

SURVIVAL_MODES = ["zipcode", "california", "nhsta"]
EV_SCENARIOS = ["BAU", "ACCII"]

combinations = [(s, e) for s in SURVIVAL_MODES for e in EV_SCENARIOS]

for i, (survival, ev) in enumerate(combinations, 1):
    print(f"\n{'=' * 60}\nRun {i}/{len(combinations)}: survival={survival}, scenario={ev}\n{'=' * 60}")
    main(survival_mode=survival, ev_scenario=ev)

print(f"\nAll {len(combinations)} runs complete. Results in results_conditional/")
