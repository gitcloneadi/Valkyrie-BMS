import pandas as pd
import time
import requests
import os
import sys

# --- VIRTUAL HARDWARE CONFIG ---
API_URL = "http://127.0.0.1:8000/api/telemetry"
RAW_CSV = "nasa_battery_data.csv"     # single raw cycle, straight from NASA PCoE
STREAM_HZ = 10
INTERVAL = 1.0 / STREAM_HZ
HTTP_TIMEOUT = 0.20
DROP_WARN_THRESHOLD = 0.05

def infer_mode(df: pd.DataFrame) -> str:
    """Raw single-cycle files have no 'mode' column. Infer it from current sign:
    negative Current_measured = discharge, positive/near-zero = charge."""
    avg_current = df["Current_measured"].mean()
    return "discharge" if avg_current < 0 else "charge"


def boot_virtual_mcu():
    if not os.path.exists(RAW_CSV):
        sys.exit(f"FATAL: {RAW_CSV} missing.")

    print(">>> BOOTING VIRTUAL MCU (single-cycle mode)...")
    df = pd.read_csv(RAW_CSV)

    required = {"Voltage_measured", "Current_measured", "Temperature_measured", "Time"}
    missing = required - set(df.columns)
    if missing:
        sys.exit(f"FATAL: raw CSV missing expected columns: {missing}")

    mode = infer_mode(df)
    cycle_id = 1  # single file = single cycle; bump this if you loop multiple files later

    session = requests.Session()
    packets_dropped = 0
    packets_sent = 0
    next_tick = time.perf_counter()

    print(f"Cycle {cycle_id} | Mode: {mode.upper()} | Rows: {len(df)}")
    print(f"Target Frequency: {STREAM_HZ}Hz. Beginning transmission.")

    try:
        while True:
            for index, row in df.iterrows():
                payload = {
                    "cycle_id": cycle_id,
                    "mode": mode,
                    "voltage": round(float(row["Voltage_measured"]), 4),
                    "current": round(float(row["Current_measured"]), 4),
                    "temperature": round(float(row["Temperature_measured"]), 4),
                    "elapsed_s": round(float(row["Time"]), 2),
                }

                try:
                    session.post(API_URL, json=payload, timeout=HTTP_TIMEOUT)
                    packets_sent += 1
                except requests.exceptions.RequestException:
                    packets_dropped += 1

                # Drift-correcting scheduler: absolute next-tick, not relative sleep.
                next_tick += INTERVAL
                now = time.perf_counter()
                if next_tick > now:
                    time.sleep(next_tick - now)
                else:
                    next_tick = now

                total = packets_sent + packets_dropped
                if index % 20 == 0:
                    drop_rate = packets_dropped / total if total else 0
                    flag = " [DEGRADED LINK]" if drop_rate > DROP_WARN_THRESHOLD else ""
                    print(
                        f"Tx Row {index} | V: {payload['voltage']}V | "
                        f"I: {payload['current']}A | T: {payload['temperature']}C | "
                        f"Sent: {packets_sent} | Dropped: {packets_dropped}{flag}          ",
                        end="\r",
                    )
            print(f"\n--- Cycle {cycle_id} completed. Restarting from row 0 as cycle {cycle_id + 1} ---")
            cycle_id += 1
    except KeyboardInterrupt:
        print("\n>>> VIRTUAL MCU INTERRUPTED BY USER.")
    finally:
        session.close()
        print(f"\n>>> VIRTUAL MCU HALTED. Sent: {packets_sent}, Dropped: {packets_dropped}")


if __name__ == "__main__":
    boot_virtual_mcu()