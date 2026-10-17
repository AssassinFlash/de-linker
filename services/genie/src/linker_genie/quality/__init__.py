"""The after-the-fact quality check of live Genie turns (#258).

docs/specs/33-judge-bakeoff.md, "部署目标": a queue-driven background worker on
the VPS judges every answer the service shipped — grounded, appropriate, and
whether the recommendation beats a wrong pick — and verifies its citations.
It is never on the answer path (owner 2026-10-17: answers ship at once; the
check runs afterwards). The queue is the service's own turn log; the verdicts
go to WordPress, where the team reads them beside the conversation.

Jev (typesafe/jev-1.13, OpenRouter /api/v1/systemone only) judges first;
deepseek-flash (official API only) judges what Jev was unsure of. A failed
call is reported and retried, never replaced by another model (AGENTS.md §5).
"""
