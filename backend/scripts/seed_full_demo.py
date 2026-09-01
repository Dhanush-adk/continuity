"""Prepare the complete Acme procurement dashboard demo."""

from app.db.session import SessionLocal
from scripts.seed_procurement_demo import seed_authorization_demo


def main() -> None:
    db = SessionLocal()
    try:
        agent, _, _, _, _, allowed, denied, reviewed = seed_authorization_demo(db)
        print("Continuity demo seeded")
        print(f"Agent: {agent.external_agent_id} (v1.1.0)")
        print(f"ALLOW: {allowed.decision_id}")
        print(f"DENY: {denied.decision_id}")
        print(f"REVIEW: {reviewed.decision_id}")
        print("Open http://localhost:3000 after starting the frontend.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
