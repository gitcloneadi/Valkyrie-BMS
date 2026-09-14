# Valkyrie-BMS: IoT Battery Telemetry & Monitoring Platform

Valkyrie-BMS is an **IoT-style telemetry platform** for Battery Management System (BMS) monitoring. It streams real-time voltage, current, and temperature data — replayed from NASA's PCoE battery aging datasets — through a WebSocket pipeline into a live dashboard, the same pattern used in production IoT device monitoring (sensor node → broker → live UI).

The telemetry schema is designed to be **device-portable**: it uses a compact, checksum-framed packet format compatible with UART transmission, so the same "sensor node" logic could run on a real embedded device (e.g. STM32) instead of the current Python simulation, without changing the broker or dashboard.

## 🚀 Overview

The platform simulates a battery "sensor node" pushing telemetry at controlled intervals, and validates the same state-estimation (SoC) and fault-detection logic that would run on a real IoT edge device — useful for building and testing the cloud/dashboard side of an IoT product before hardware is ready.

### Core Capabilities

* **Data Pipeline**: Consolidates raw NASA battery datasets into a standardized, timestamped telemetry schema.
* **Virtual Sensor Node**: `virtual_mcu.py` acts as the IoT device — computing Coulomb counting and fault logic, then emitting telemetry packets.
* **IoT Broker**: A FastAPI backend with SQLite ingesting device data and broadcasting it to subscribed clients over WebSockets — the same broker/pub-sub pattern used in MQTT-style IoT stacks.
* **Live Telemetry Dashboard**: Real-time cell state, thermal profile, and power visualization, updated push-style (no polling).

## 🏗️ Architecture

* **Virtual device layer:** `virtual_mcu.py` simulates the edge device — running Coulomb counting + fault logic locally and pushing JSON telemetry to the broker.
* **Broker layer :** `main.py`  ingests device payloads, persists them to SQLite, and fans them out to connected dashboard clients via WebSocket.
* **Physical device layer :** The packet framing mirrors what a UART-connected microcontroller would send, so a real embedded sensor node could be swapped in later without touching the broker or UI.

## 🛠️ Tech Stack

* **Device simulation**: Python 
* **Broker / backend**: FastAPI, Uvicorn, SQLite3 (WAL mode), WebSockets
* **Dashboard**: HTML/CSS/JS, live WebSocket updates
* **Data processing**: Pandas, Requests
* **Target edge hardware **: STM32 ARM Cortex over UART

## 🚦 Quick Start

1. **Start the broker:**
```bash
   uvicorn main:app
```
2. **Start the virtual sensor node:**
```bash
   python virtual_mcu.py
```
3. **Open the dashboard:**
   Open `valkyrie_dashboard.html` in your browser to view live telemetry.
