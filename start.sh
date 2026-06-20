#!/bin/bash
python main.py &
uvicorn webapp.app:app --host 0.0.0.0 --port $PORT
