# BMS-HIL: Digital Twin & Hardware-in-the-Loop Framework

This project implements a **Real-Time Hardware-in-the-Loop (HIL) Verification Framework** for a Battery Management System (BMS). It uses NASA’s PCoE battery aging datasets to simulate real-world battery physics and stream them to an external controller (e.g., STM32) for state estimation and fault detection.

## 🚀 Overview

The system bridges the gap between static datasets and real-time hardware testing. By "streaming" physics-accurate battery data over UART at high frequencies (100Hz), we can test BMS algorithms (like SoC estimation or Fault Detection) without needing a physical battery pack.

### Key Features

* **Data Pipeline**: Cleans and consolidates NASA battery datasets into a standardized schema for HIL.
* **Real-Time Streaming**: High-speed serial communication (460,800 baud) using a custom packet protocol.
* **Digital Twin Simulation**: Python-based simulation of voltage/current waveforms with fault injection capabilities ('i' to inject, 'n' for normal).
* **Telemetry Visualization**: Real-time plotting of State of Charge (SoC) and Voltage using Matplotlib.

## 📁 Project Structure

* `data_sorter.py`: Refines thousands of CSV files into a master `cleaned.csv`, aligning charge/discharge modes.
* `nasa_streamer.py`: The HIL engine. Streams master dataset physics (V, I, T) to the hardware at 100Hz.
* `digital_twin_test.py`: A simulation tool to test the protocol and visualization without the NASA dataset.

## 🛠 Tech Stack

* **Languages**: Python, Verilog/C (for the hardware side).
* **Protocols**: UART, Custom Binary Packet (Sync: `0xAA 55`, XOR Checksum).
* **Libraries**: Pandas, Serial, Matplotlib, Struct, TQDM.

## 📊 Protocol Specification

The framework uses a 16-byte frame for efficiency:
| Header (2B) | Msg ID (1B) | Data A (4B - Float) | Data B (4B - Float) | Data C (4B - Float) | Checksum (1B) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0xAA 55` | `0x01` | Voltage | Current | Temperature | XOR |

## 🚦 Getting Started

1. **Clean the Data**:
`python data_sorter.py`
2. **Run the HIL Stream**:
Connect your STM32/Microcontroller to `COM8` (or your specific port) and run:
`python nasa_streamer.py`
3. **Simulate a Fault**:
Run `digital_twin_test.py` and hold the 'i' key to trigger a fault state in the telemetry.

## 🖥️ Running the SIL Dashboard

1. **Start the API Broker**:
   Run the FastAPI server. **Do not use `--reload`** for interviews/demos, as file saves will reset the DB and drop the MCU connection mid-stream.
   ```bash
   uvicorn main:app
   ```
2. **Start the Virtual MCU**:
   Run the virtual MCU to stream single-cycle data to the API:
   ```bash
   python virtual_mcu.py
   ```
3. **Launch the Dashboard**:
   Start the Streamlit UI:
   ```bash
   streamlit run app.py
   ```

---
