#!/usr/bin/env bash
# Launch the full Tribunal agent society. Each agent prints its address on boot —
# paste those into .env (the *_ADDRESS vars), then restart so they can find each other.
#
# Boot order: leaf/specialist agents first, orchestrator last.
set -a; [ -f .env ] && . ./.env; set +a

cd "$(dirname "$0")/agents"

echo "Starting Tribunal agents... (Ctrl+C to stop all)"
python policy_rag_agent.py   & P1=$!
python formreader_agent.py   & P2=$!
python dialogue_agent.py     & P3=$!
python interpreter_agent.py  & P4=$!
python review_agent.py       & P5=$!
sleep 2
python orchestrator.py       & P6=$!

trap "kill $P1 $P2 $P3 $P4 $P5 $P6 2>/dev/null" EXIT
wait
