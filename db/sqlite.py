# db/sqlite.py
import os
import sqlite3
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver

_DB_DIR = Path(__file__).parent.parent / "runs"
_DB_DIR.mkdir(exist_ok=True)

_conn = sqlite3.connect(str(_DB_DIR / "agent_runs.db"), check_same_thread=False)
checkpointer = SqliteSaver(_conn)
