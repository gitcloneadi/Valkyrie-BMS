from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from contextlib import asynccontextmanager
import sqlite3
import json

DB_FILE = "telemetry.db"


class ConnectionManager:
    """Tracks connected dashboard WebSocket clients and pushes each new
    telemetry row to all of them as it arrives — this is what makes the
    dashboard 'live' instead of polling."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, payload: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


def get_connection(timeout: float = 5.0) -> sqlite3.Connection:
    """Every connection gets a busy_timeout so concurrent reads/writes
    wait and retry instead of failing immediately with 'database is locked'."""
    conn = sqlite3.connect(DB_FILE, timeout=timeout)
    conn.execute("PRAGMA busy_timeout = 5000;")  # ms — belt-and-suspenders with `timeout=`
    return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        # CRITICAL: Write-Ahead Logging lets one writer and many readers
        # work concurrently instead of blocking each other. This setting
        # is persisted in the database file itself once set.
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS battery_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
                cycle_id INTEGER,
                mode TEXT,
                voltage REAL,
                current REAL,
                temperature REAL,
                elapsed_s REAL
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON battery_data(timestamp)"
        )
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Correct FastAPI lifecycle hook — runs once at startup, safe under
    # --reload and safe if you ever add --workers > 1.
    init_db()
    yield


app = FastAPI(title="Valkyrie BMS Telemetry API", lifespan=lifespan)


class TelemetryPayload(BaseModel):
    cycle_id: int
    mode: str
    voltage: float
    current: float
    temperature: float
    elapsed_s: float | None = None  # matches virtual_mcu.py's Time field


@app.post("/api/telemetry")
async def receive_telemetry(data: TelemetryPayload):
    """Ingests data from the Virtual MCU: writes to SQLite AND broadcasts
    to every connected dashboard over WebSocket in the same request."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO battery_data (cycle_id, mode, voltage, current, temperature, elapsed_s)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (data.cycle_id, data.mode, data.voltage, data.current, data.temperature, data.elapsed_s))
            conn.commit()

        # Push this exact row straight to the dashboard(s) — no polling delay.
        await manager.broadcast({
            "cycle_id": data.cycle_id,
            "mode": data.mode,
            "voltage": data.voltage,
            "current": data.current,
            "temperature": data.temperature,
            "elapsed_s": data.elapsed_s,
            "fault": False,
        })

        return {"status": "success", "message": "Telemetry logged"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=503, detail=f"Database busy or unavailable: {e}")


@app.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket):
    """The dashboard connects here. Each POST to /api/telemetry gets
    pushed out to every connection currently open on this endpoint."""
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect the dashboard to send anything, but this
            # keeps the connection alive and detects disconnects cleanly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/telemetry/latest")
def get_latest_telemetry(limit: int = 100, last_id: int = 0):
    """Provides the latest data chunk for the Streamlit dashboard."""
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM (
                    SELECT id, timestamp, cycle_id, mode, voltage, current, temperature, elapsed_s
                    FROM battery_data
                    WHERE id > ?
                    ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
            """, (last_id, limit))
            rows = cursor.fetchall()
        return {"status": "success", "data": [dict(row) for row in rows]}
    except sqlite3.Error as e:
        raise HTTPException(status_code=503, detail=f"Database busy or unavailable: {e}")


@app.get("/api/health")
def health_check():
    """Quick liveness check — handy to confirm the broker is up before starting the MCU."""
    return {"status": "ok"}