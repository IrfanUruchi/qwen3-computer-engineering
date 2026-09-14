DOMAIN_TARGETS = {
    "software-engineering": 90,
    "systems-programming": 85,
    "operating-systems": 80,
    "computer-architecture": 75,
    "linux-infrastructure": 70,
    "embedded-systems": 60,
    "networking": 60,
    "distributed-systems": 60,
    "compute-model-infrastructure": 50,
    "secure-engineering": 35,
    "engineering-reasoning": 35,
}

DIFFICULTY_TARGETS = {
    "intermediate": 140,
    "advanced": 385,
    "expert": 175,
}

TASK_GROUP_TARGETS = {
    "implementation-code": 175,
    "debug-failure": 175,
    "performance": 140,
    "architecture-design": 140,
    "testing-config": 70,
}

TASK_GROUPS = {
    "implementation-code": {"implementation", "code-repair", "code-generation"},
    "debug-failure": {"debugging", "failure-analysis", "troubleshooting"},
    "performance": {"performance-analysis"},
    "architecture-design": {"architecture-analysis", "design", "technical-decision"},
    "testing-config": {"testing", "configuration"},
}
