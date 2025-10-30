from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import time
import json

app = FastAPI()

# Simulated alerts
alerts = []

@app.post("/send-alert")
async def send_alert(message: str):
    alerts.append({"message": message})
    return {"status": "Alert sent!"}

@app.get("/alerts/stream")
async def alert_stream():
    def event_generator():
        last_index = 0
        while True:
            if len(alerts) > last_index:
                for alert in alerts[last_index:]:
                    yield f"data: {json.dumps(alert)}\n\n"
                last_index = len(alerts)
            time.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
