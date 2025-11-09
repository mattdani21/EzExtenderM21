from app.precedent import record_precedent

cases = [
    ("My grandfather passed away", "allow"),
    ("Death in the family, need time for funeral", "allow"),
    ("Cold/flu for two days", "deny"),
    ("Common cold, minor symptoms", "deny"),
    ("Hospitalized for surgery, recovery expected 1 week", "allow"),
]
for i,(reason,outcome) in enumerate(cases,1):
    record_precedent(reason, outcome, days_requested=None, reviewer=f"seed{i}")
print("Seeded.")
