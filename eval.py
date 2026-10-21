import subprocess, sys, time

# (question, tool the agent SHOULD call, or None if it should decline)
TESTS = [
    ("Is property 0000010005R in a flood zone?", "flood_risk"),
    ("What is the median home value in 32207?", "zip_stats"),
    ("What have homes sold for recently in 32210?", "recent_sales"),
    ("Find condos under 200000 in 32256", "search_properties"),
    ("Show me details for property 0000010005R", "property_details"),
    ("Single family homes in 32205 not in a high risk flood zone", "search_properties"),
    ("Which ZIP is cheaper, 32205 or 32210?", "zip_stats"),
    ("What's the weather in Jacksonville today?", None),
]

passed = 0
for q, expected in TESTS:
    t = time.time()
    out = subprocess.run(
        [sys.executable, "agent.py", q], capture_output=True, text=True
    ).stdout
    called = [
        l.split("calling ")[1].split("(")[0]
        for l in out.splitlines()
        if "-> calling" in l
    ]
    ok = (expected in called) if expected else not called
    passed += ok
    print(
        f"{'PASS' if ok else 'FAIL'}  {time.time() - t:5.1f}s  {q}\n      expected={expected} called={called}"
    )

print(f"\n{passed}/{len(TESTS)} passed")
