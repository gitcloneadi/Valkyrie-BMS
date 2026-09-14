import pandas as pd
import serial
import time
import struct
import os

# --- CONFIGURATION ---
SERIAL_PORT = 'COM8'  # Your confirmed port
BAUD_RATE = 460800
MASTER_CSV = 'nasa_battery_master_cleaned.csv'
STREAM_HZ = 100 
INTERVAL = 1.0 / STREAM_HZ

def calc_checksum(payload):
    """Simple XOR checksum for protocol integrity."""
    chk = 0
    for b in payload:
        chk ^= b
    return chk

def stream_master_dataset():
    # 1. Load the Master Dataset
    if not os.path.exists(MASTER_CSV):
        print(f"FATAL: {MASTER_CSV} not found. Run the data_sorter.py first!")
        return

    print(f"Loading Master Dataset: {MASTER_CSV}...")
    # Using chunksize or dtype optimization for large files
    df = pd.read_csv(MASTER_CSV, dtype={'mode': 'category'})
    print(f"Loaded {len(df)} rows of battery history.")

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
    except Exception as e:
        print(f"Serial Error: {e}")
        return

    print(">>> STARTING HIL STREAM...")
    
    current_cycle = -1

    for index, row in df.iterrows():
        start_time = time.perf_counter()

        # 2. IDENTIFY THE STATE
        # msg_id: 0x01 = Discharge (Car Driving), 0x03 = Charge (Car Plugged In)
        msg_id = 0x01 if row['mode'] == 'discharge' else 0x03
        
        # Log when we enter a new cycle
        if row['cycle_id'] != current_cycle:
            current_cycle = int(row['cycle_id'])
            print(f"\n[Cycle {current_cycle}] Mode: {row['mode'].upper()}")

        # 3. EXTRACT PHYSICS
        v = float(row['Voltage_measured'])
        i = float(row['Current_measured'])
        temp = float(row['Temperature_measured'])

        # 4. PACK DATA (ID 0x01/0x03, V, I, T)
        # Format: < (Little Endian) B (1 byte ID) fff (3 floats)
        payload = struct.pack('<Bfff', msg_id, v, i, temp)
        checksum = calc_checksum(payload)
        
        # Frame: Sync (2) + Payload (13) + Checksum (1) = 16 Bytes
        frame = b'\xAA\x55' + payload + bytes([checksum])
        ser.write(frame)

        # 5. PACING (100Hz)
        elapsed = time.perf_counter() - start_time
        if elapsed < INTERVAL:
            time.sleep(INTERVAL - elapsed)

        # Telemetry every 200 rows to keep the console clean
        if index % 200 == 0:
            print(f"Row {index} | V: {v:.3f}V | I: {i:.3f}A | Mode: {msg_id}", end='\r')

    print("\nStream Finished. Battery EOL (End of Life) reached.")
    ser.close()

if __name__ == "__main__":
    stream_master_dataset()