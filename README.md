# Valkyrie-BMS: Software-in-the-Loop Battery Telemetry & Verification Framework

This project implements a **Software-in-the-Loop (SIL) simulation framework** for Battery Management System (BMS) verification, built around NASA's PCoE battery aging datasets to reproduce real-world cell behavior (Voltage, Current, Temperature) at controlled frequencies.

The system is designed with a **hardware-portable packet schema**, so the same telemetry format and fault-logic contract used here could be dropped onto a real MCU (e.g. STM32) over UART for Hardware-in-the-Loop testing — that path is a design goal / next step, not something benchmarked on physical hardware yet.

## 🚀 Overview

The framework replays physics-accurate battery data to validate BMS state-estimation (SoC) and fault-detection logic under dynamic load conditions, without requiring physical hardware in the loop.

### Core Capabilities

* **Data Pipeline**: Consolidates raw NASA battery datasets into a standardized, timestamped schema.
* **Virtual MCU**: `virtual_mcu.py` runs Coulomb counting and fault logic in Python, emitting telemetry on the same schema a real MCU firmware would use.
* **Broker**: A FastAPI backend with SQLite (WAL mode) persisting samples and broadcasting them to clients over WebSockets.
* **Live Telemetry UI**: Real-time cell state, thermal profile, and power dissipation, rendered in a custom dashboard.

## 🏗️ Architecture

* **SIL Path (implemented):** `virtual_mcu.py` computes Coulomb counting + fault logic in Python and pushes JSON payloads to `main.py`, which persists to SQLite and broadcasts over WebSocket to the dashboard.
* **HIL Path (designed for, not yet built):** The packet schema is UART-compatible by design (sync bytes, checksum framing) so a real STM32 target could replace the virtual MCU without changing the broker or UI.

## 🛠️ Tech Stack

* **Simulation / Logic**: Python (Coulomb counting, fault-detection state machine)
* **Backend Broker**: FastAPI, Uvicorn, SQLite3 (WAL mode)
* **Frontend UI**: HTML/CSS/JS over WebSockets
* **Data Processing**: Pandas, Requests
* **Target hardware (planned)**: STM32 ARM Cortex over UART

## 🚦 Quick Start

1. **Start the backend broker:**
```bash
   uvicorn main:app
```
2. **Run the virtual MCU simulation:**
```bash
   python virtual_mcu.py
```
3. **Open the dashboard:**
   Open `valkyrie_dashboard.html` in your browser to view live telemetry.
