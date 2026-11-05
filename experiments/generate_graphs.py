import os
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_FILE = os.path.join(BASE_DIR, "results", "summary.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "results", "graphs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(CSV_FILE)

# Remove whitespace from CSV column names
df.columns = df.columns.str.strip()

required = [
    "scenario", "queries", "servers",
    "success_rate_percent", "average_latency_ms",
    "throughput_qps", "p95_latency_ms"
]

missing = [col for col in required if col not in df.columns]
if missing:
    raise ValueError(f"Missing CSV columns: {missing}")

# Select comparable normal workload experiments:
# 100 queries with 1, 3 and 5 servers.
comparison = df[
    (df["scenario"] == "normal") &
    (df["queries"] == 100) &
    (df["servers"].isin([1, 3, 5]))
].sort_values("servers")

if comparison.empty:
    raise ValueError("No matching 100-query normal benchmark records found.")

metrics = [
    ("average_latency_ms", "Average Latency", "Milliseconds",
     "average_latency_comparison.png"),
    ("throughput_qps", "Throughput", "Queries per second",
     "throughput_comparison.png"),
    ("success_rate_percent", "Success Rate", "Percentage",
     "success_rate_comparison.png"),
    ("p95_latency_ms", "P95 Latency", "Milliseconds",
     "p95_latency_comparison.png"),
]

for column, title, ylabel, filename in metrics:
    plt.figure(figsize=(9, 5))
    plt.bar(
        comparison["servers"].astype(str),
        comparison[column]
    )
    plt.title(f"{title} — 100 Queries")
    plt.xlabel("Number of DNS Servers")
    plt.ylabel(ylabel)
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    output = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(output, dpi=300)
    plt.close()

    print(f"Generated: {output}")

# Separate negative-lookup experiment
missing_data = df[df["scenario"] == "missing"]

if not missing_data.empty:
    row = missing_data.iloc[0]

    plt.figure(figsize=(8, 5))
    plt.bar(
        ["NOT_FOUND", "FAILED"],
        [row["not_found"], row["failed"]]
    )
    plt.title("Missing-Domain Test Results")
    plt.ylabel("Number of Queries")
    plt.tight_layout()

    output = os.path.join(OUTPUT_DIR, "missing_domain_results.png")
    plt.savefig(output, dpi=300)
    plt.close()

    print(f"Generated: {output}")

print("\nAll graphs generated successfully.")
print(f"Output folder: {OUTPUT_DIR}")
