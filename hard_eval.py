import os, subprocess, sys, time

# (question, tools the agent MUST call; [] means it should decline)
TESTS = [
    (
        "Is the most expensive single family home in 32207 in a flood zone?",
        ["search_properties", "flood_risk"],
    ),
    (
        "Compare median values in 32205 and 32207 and show recent sales in the cheaper one",
        ["zip_stats", "recent_sales"],
    ),
    (
        "Find condos in 32256 and tell me the flood zone of the first one",
        ["search_properties", "flood_risk"],
    ),
    (
        "What did property 0000010005R last sell for and is it in a flood zone?",
        ["flood_risk"],
    ),
    (
        "Show me mobile homes under 100000 in 32218 outside high risk flood zones",
        ["search_properties"],
    ),
    ("What is the Zestimate for 123 Fake Street?", []),
    ("Tell me a joke about Jacksonville", []),
    ("What did property 0000010005R last sell for?", ["sale_history"]),
]
MODEL = os.environ.get("AGENT_MODEL", "qwen3-coder:30b")

passed = 0
for q, expected in TESTS:
    t = time.time()
    out = subprocess.run(
        [sys.executable, "agent.py", q],
        capture_output=True,
        text=True,
        env={**os.environ, "AGENT_MODEL": MODEL},
    ).stdout
    called = [
        l.split("calling ")[1].split("(")[0]
        for l in out.splitlines()
        if "-> calling" in l
    ]
    ok = all(e in called for e in expected) if expected else not called
    passed += ok
    answer = out.split("Answer:")[-1].strip()[:200].replace("\n", " ")
    print(
        f"{'PASS' if ok else 'FAIL'}  {time.time() - t:5.1f}s  {q}\n      called={called}\n      answer: {answer}\n"
    )
print(f"{passed}/{len(TESTS)} passed ({MODEL})")
