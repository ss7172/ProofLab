W=/Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/digital-twin
cd /Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/maveric && source .venv/bin/activate && export PYTHONPATH="$PWD"
echo "[$(date -u +%T)] 2. ask: example_app.py"; s=$(date +%s)
python3 apps/example/example_app.py > $W/ask.out 2>&1; echo "   exit=$? in $(( $(date +%s)-s ))s"
echo "[$(date -u +%T)] 3. feed: retrain with ue_training_data_2.csv (model_update=True)"; s=$(date +%s)
python3 - > $W/feed.out 2>&1 <<'PY'
from dotenv import load_dotenv
load_dotenv()
import pandas as pd
from radp.client.client import RADPClient
from radp.client.helper import RADPHelper

client = RADPClient()
r = client.train(
    model_id="tokyo-rf-twin",
    params={},
    ue_training_data=pd.read_csv("apps/example/data/ue_training_data_2.csv"),
    topology=pd.read_csv("apps/example/data/topology.csv"),
    model_update=True,
)
status = RADPHelper(client).resolve_model_status(
    model_id=r["model_id"], wait_interval=10, max_attempts=60,
    verbose=False, job_id=r["job_id"])
print("model updated:", status.success)
PY
echo "   exit=$? in $(( $(date +%s)-s ))s"
echo "[$(date -u +%T)] checkpoint: example_app.py again"; s=$(date +%s)
python3 apps/example/example_app.py > $W/checkpoint.out 2>&1; echo "   exit=$? in $(( $(date +%s)-s ))s"
