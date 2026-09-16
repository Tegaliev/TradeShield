import json
import os

RESULTS_DIR = 'results'

SCENARIOS = {
    "baseline": {"vol_multiplier": 1.0, "description": "Текущие рыночные условия"},
    "geopolitical_shock": {"vol_multiplier": 1.4, "description": "Рост геополитической напряженности (+40% к волатильности)"},
    "fed_rate_hike": {"vol_multiplier": 1.25, "description": "Агрессивный рост процентных ставок (+25% к волатильности)"},
    "global_recession": {"vol_multiplier": 1.7, "description": "Масштабный рецессионный шок (+70% к волатильности)"}
}

def run_stress_test(base_var_usd, base_vol_pct, scenario_key="geopolitical_shock"):
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["baseline"])
    mult = scenario["vol_multiplier"]

    stressed_vol = base_vol_pct * mult
    stressed_var = base_var_usd * mult

    res = {
        "scenario_name": scenario_key,
        "description": scenario["description"],
        "base_var_usd": round(base_var_usd, 2),
        "stressed_var_usd": round(stressed_var, 2),
        "var_increase_usd": round(stressed_var - base_var_usd, 2),
        "stressed_vol_pct": round(stressed_vol, 2)
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, 'stress_test_result.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=4, ensure_ascii=False)

    return res

if __name__ == '__main__':
    print(run_stress_test(5000, 12.5, "geopolitical_shock"))
