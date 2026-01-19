#!/bin/bash

# Stop all running processes

echo "Stopping PhD Task Manager..."

# Kill backend (Python)
pkill -f "python main.py"

# Kill frontend (npm/vite)
pkill -f "vite"

echo "✓ Stopped"
