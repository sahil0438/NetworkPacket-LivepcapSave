# 🌐 Network Packet Analyzer — with PCAP Save

A Wireshark-inspired **Network Packet Analyzer** with **real-time packet capture and PCAP file saving**. Built with **React + Vite** frontend and a **Python Flask + WebSocket** backend. Captured packets are saved as `.pcap` files during live sniffing — so you can open and analyze them later in Wireshark, just like a real network forensics tool.

---

## 📋 Table of Contents

- [About](#about)
- [What Makes This Different](#what-makes-this-different)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Running the App](#running-the-app)
- [PCAP File Usage](#pcap-file-usage)
- [Build for Production](#build-for-production)
- [Credits](#credits)

---

## About

This project captures live network packets from your Wi-Fi or network interface, streams them to a React dashboard in real time via WebSockets, and simultaneously **saves them as a `.pcap` file**. This means if an attack or suspicious activity occurs, the full packet data is preserved and can be loaded directly into **Wireshark** for deep forensic analysis later.

---

## What Makes This Different

| Feature | Basic Analyzer | This Project |
|---|---|---|
| Live packet display | ✅ | ✅ |
| Real-time WebSocket stream | ✅ | ✅ |
| **Save packets as PCAP file** | ❌ | ✅ |
| **Open captures in Wireshark later** | ❌ | ✅ |
| **Axios HTTP calls** | ❌ | ✅ |
| Forensic / post-incident analysis | ❌ | ✅ |

---

## Features

- 📡 **Live packet sniffing** on your Wi-Fi / network interface
- 🔌 **Real-time streaming** via WebSocket (`ws://localhost:5000/ws`)
- 💾 **Auto-saves captured packets as `.pcap` file** during live sniffing
- 🦈 **PCAP files are fully compatible with Wireshark** for later analysis
- 🚨 **Useful for attack detection** — if something suspicious happens, the packets are already saved
- 📊 **Traffic charts** using Recharts and Chart.js
- 🔍 **Packet filtering** by protocol, IP, port, etc.
- 📁 **Export packet data** from the browser (via file-saver)
- 🌙 **Dark-themed UI** inspired by Wireshark
- ⚡ **Fast frontend** powered by Vite 6 + React 18

---

## Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| React 18 | UI framework |
| Vite 6 | Build tool and dev server (port 3000) |
| Tailwind CSS 3 | Styling |
| Axios | HTTP requests to Flask backend |
| Recharts | Traffic/protocol charts |
| Chart.js | Additional data visualizations |
| Lucide React | Icons |
| file-saver | Export data from browser |

### Backend
| Technology | Purpose |
|---|---|
| Python | Backend runtime |
| Flask | Web server (port 5000) |
| Flask-SocketIO / WebSocket | Real-time packet streaming |
| Scapy | Live packet sniffing + PCAP file writing |
| venv | Python virtual environment |

---

## Project Structure

```
packet-analyzer/
│
├── src/                        # React frontend source
│   ├── main.jsx                # App entry point
│   └── (components, pages...)
│
├── backend/                    # Python Flask backend
│   ├── server.py               # Main server — Flask + WebSocket
│   └── captures/               # Saved .pcap files stored here
│
├── venv/                       # Python virtual environment (not committed)
├── node_modules/               # Node dependencies (not committed)
│
├── index.html                  # HTML entry point
├── vite.config.js              # Vite config (port 3000)
├── tailwind.config.js          # Tailwind CSS config
├── postcss.config.js           # PostCSS config
├── package.json                # Node dependencies & scripts
├── package-lock.json           # Lockfile
└── README.md
```

---

## Prerequisites

- **Node.js** v18 or higher — [Download](https://nodejs.org)
- **Python** 3.8 or higher — [Download](https://python.org)
- **Wireshark** (optional, for opening saved `.pcap` files) — [Download](https://www.wireshark.org/)
- ⚠️ **Administrator / root privileges** required for live packet sniffing

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/packet-analyzer.git
cd packet-analyzer
```

### 2. Install frontend dependencies

```bash
npm install
```

### 3. Set up the Python backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

cd ..
```

---

## Running the App

> ⚠️ You need **two separate terminals** — one for the backend, one for the frontend.

### Terminal 1 — Start the Backend (as Administrator)

Open **Command Prompt as Administrator**, then:

```bash
cd path\to\packet-analyzer\backend

python server.py
```

Expected output:
```
INFO: Server starting on http://0.0.0.0:5000
INFO: WebSocket available on ws://0.0.0.0:5000/ws
* Serving Flask app 'server'
* Running on http://127.0.0.1:5000
```

> 💡 On Linux/macOS: `sudo python server.py`

### Terminal 2 — Start the Frontend

```bash
npm run dev
```

Expected output:
```
VITE v6.3.5  ready in ~1453 ms

➜  Local:   http://localhost:3000/
```

Open **http://localhost:3000** in your browser.

---

## PCAP File Usage

While packets are being captured, the backend **automatically writes them to a `.pcap` file** in real time. This means:

- If a **network attack** or anomaly occurs, the packets are already saved even before you stop the capture
- Once capture is stopped (or while it's running), you can open the `.pcap` file directly in **Wireshark**

### Opening the PCAP in Wireshark

1. Open **Wireshark**
2. Go to **File → Open**
3. Navigate to `backend/captures/`
4. Select the `.pcap` file
5. Analyze your packets with full Wireshark features — filters, protocol dissection, stream following, etc.

---

## Build for Production

```bash
npm run build
npm run preview
```

---

## Credits

- Inspired by [Wireshark](https://www.wireshark.org/)
- Packet capture powered by [Scapy](https://scapy.net/)
- Charts by [Recharts](https://recharts.org/) and [Chart.js](https://www.chartjs.org/)
- Built with [Vite](https://vitejs.dev/) + [React](https://react.dev/) + [Tailwind CSS](https://tailwindcss.com/) + [Flask](https://flask.palletsprojects.com/)
