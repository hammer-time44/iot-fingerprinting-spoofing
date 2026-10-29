import sys, os
sys.path.insert(0, os.path.abspath("."))
import warnings
warnings.filterwarnings('ignore')
import time
from network_guard.backend.benchmark import run_benchmark

print("Starting Network Defense Lab benchmark (N=30 trials per scenario)...")
t0 = time.time()
res = run_benchmark(n_trials=30)
t1 = time.time()
print(f"Benchmark finished in {t1 - t0:.2f} seconds!")

print("\n--- BENCHMARK RESULTS ---")
for sc, d in res["summary"].items():
    print(f"Scenario: {sc:18} | Detection: {d['detection_rate_pct']:6.2f}% | Mean WTD: {str(d['mean_windows_to_detect']):>5} | FA Rate: {d['false_alarm_rate_pct']:4.2f}%")

print("\n--- TIMING MIMICRY CURVE ---")
for m in res["mimicry_curve"]:
    print(f"Strength {m['strength']:3.1f}: Detection {m['detection_rate_pct']:6.2f}%")
