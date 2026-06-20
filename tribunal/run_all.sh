#!/usr/bin/env bash
# Launch the full Tribunal agent society. Each agent prints its address on boot —
# paste those into .env (the *_ADDRESS vars), then restart so they can find each other.
#
# Boot order: leaf agents first, orchestrator last.
set -a; [ -f .env ] && . ./.env; set +a

cd "$(dirname "$0")/agents"

echo "Starting Tribunal agents... (Ctrl+C to stop all)"
python policy_rag_agent.py   & P1=$!
python eligibility_agent.py  & P2=$!
python formfiller_agent.py   & P3=$!
python translator_agent.py   & P4=$!
sleep 2
python orchestrator.py       & P5=$!

trap "kill $P1 $P2 $P3 $P4 $P5 2>/dev/null" EXIT
wait
