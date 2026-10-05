# Query the trained tokyo-rf-twin directly (example_app.py uses its own example_test_model).
import json, re, sys
from dotenv import load_dotenv
import os; load_dotenv(os.path.join(os.getcwd(), ".env"))
import pandas as pd
from radp.client.client import RADPClient
from radp.client.helper import RADPHelper
D = "apps/example/data"
ev_file = f"{D}/example_sim_data.json"
pred_files = [f"{D}/ue_data_1.csv", f"{D}/ue_data_2.csv"]
cfg_file = f"{D}/config.csv"
event = json.load(open(ev_file))
def set_model(o):
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "model_id": o[k] = "tokyo-rf-twin"; n += 1
            else: n += set_model(v)
    elif isinstance(o, list):
        for v in o: n += set_model(v)
    return n
print("event file:", ev_file, "| model_id fields set to tokyo-rf-twin:", set_model(event))
client = RADPClient(); helper = RADPHelper(client)
r = client.simulation(simulation_event=event, ue_data=pd.concat([pd.read_csv(f) for f in pred_files]), config=pd.read_csv(cfg_file))
st = helper.resolve_simulation_status(r["simulation_id"], wait_interval=3, max_attempts=20, verbose=False, job_id=r["job_id"])
print("simulation success:", st.success)
df = client.consume_simulation_output(r["simulation_id"])
print("rows:", len(df), "| columns:", list(df.columns))
print(df.groupby("cell_id")["rxpower_dbm"].describe()[["count","mean","min","max"]].round(2))
