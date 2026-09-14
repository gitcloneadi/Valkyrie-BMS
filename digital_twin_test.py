import serial
import struct
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import math
import keyboard 

# --- CONFIGURATION ---
SERIAL_PORT = 'COM3'  # CHECK DEVICE MANAGER!
BAUD_RATE = 460800    # If this fails, we MUST drop to 115200

# Global State
fault_active = False
xs, y_soc, y_volts = [], [], []
start_time = time.time()

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"Connected to {SERIAL_PORT} @ {BAUD_RATE}")
    ser.reset_input_buffer() # Clear old junk
except Exception as e:
    print("Error opening serial:", e)
    exit()

def send_battery_data():
    global fault_active
    t = 0
    toggle = 0 # To switch between Battery and OBD packets

    while True:
        # 1. Generate Waveforms
        sim_volts = 3.8 + 0.2 * math.sin(t)
        sim_current = 0.5 + 1.5 * math.sin(t * 0.5)
        
        # Simulate RPM (1000 to 3000 RPM)
        sim_rpm = 2000 + 1000 * math.sin(t * 0.2)
        sim_speed = 60 + 20 * math.sin(t * 0.2)

        # 2. Prepare Packet
        if toggle == 0:
            # --- SEND BATTERY DATA (ID 0x01) ---
            msg_id = 0x01 
            temp = 25.0
            payload = struct.pack('<Bfff', msg_id, sim_volts, sim_current, temp)
            toggle = 1
        else:
            # --- SEND OBD DATA (ID 0x02) ---
            msg_id = 0x02
            # data_a = RPM, data_b = Speed, data_c = 0.0
            payload = struct.pack('<Bfff', msg_id, sim_rpm, sim_speed, 0.0)
            toggle = 0
        
        # Checksum & Send
        checksum = 0
        for b in payload: checksum ^= b
        packet = b'\xAA\x55' + payload + bytes([checksum])
        
        try:
            ser.write(packet)
        except:
            pass
        
        # 3. Handle Keyboard
        if keyboard.is_pressed('i') and not fault_active:
            print(">>> FAULT INJECTED <<<")
            fault_active = True
            send_command(1.0)
        elif keyboard.is_pressed('n') and fault_active:
            print(">>> NORMAL MODE <<<")
            fault_active = False
            send_command(0.0)

        t += 0.1
        time.sleep(0.05) 

def send_command(val):
    msg_id = 0x04
    payload = struct.pack('<Bfff', msg_id, val, 0.0, 0.0)
    checksum = 0
    for b in payload: checksum ^= b
    ser.write(b'\xAA\x55' + payload + bytes([checksum]))

def read_telemetry():
    global xs, y_soc, y_volts
    while True:
        try:
            # DEBUG: Uncomment this if you see NOTHING
            # if ser.in_waiting > 0: print(f"Bytes waiting: {ser.in_waiting}")
            
            if ser.in_waiting > 14:
                # Look for Header
                b1 = ser.read()
                if b1 == b'\xAA':
                    b2 = ser.read()
                    if b2 == b'\x55':
                        data = ser.read(14)
                        if len(data) == 14:
                            msg_id, soc, voltage, current, chk = struct.unpack('<BfffB', data)
                            
                            # Only plot Result Packet (ID 0x03)
                            if msg_id == 0x03:
                                print(f"STM32: SoC={soc*100:.1f}% V={voltage:.2f}V")
                                xs.append(time.time() - start_time)
                                y_soc.append(soc * 100.0)
                                y_volts.append(voltage)
                                
                                if len(xs) > 100: 
                                    xs.pop(0); y_soc.pop(0); y_volts.pop(0)
        except Exception as e:
            print("Read Error:", e)

# Start Threads
t1 = threading.Thread(target=send_battery_data, daemon=True)
t2 = threading.Thread(target=read_telemetry, daemon=True)
t1.start()
t2.start()

# Plot
print("Controls: Hold 'i' for FAULT, 'n' for NORMAL")
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)

def animate(i):
    if len(xs) == 0: return # Don't plot empty data
    
    ax1.clear(); ax2.clear()
    ax1.plot(xs, y_soc, 'g-', label='SoC %')
    ax1.set_ylabel('SoC'); ax1.legend(loc='upper right')
    ax1.grid(True)
    
    ax2.plot(xs, y_volts, 'b-', label='Voltage')
    ax2.set_ylabel('Volts'); ax2.legend(loc='upper right')
    ax2.grid(True)

# ADDED cache_frame_data=False TO FIX THE WARNING
ani = FuncAnimation(fig, animate, interval=100, cache_frame_data=False)
plt.show()