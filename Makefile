.PHONY: test verify run fleet

test:
	pytest tests/ -v

verify:
	python verifier/verifier_agent.py

run:
	uvicorn control_plane.app:app --reload --port 8000

fleet:
	python edge_agent/sim_fleet.py --n 5

quality-gate: test verify
	@echo "Quality gate passed - safe to publish"
