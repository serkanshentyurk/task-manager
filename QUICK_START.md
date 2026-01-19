# Quick Start - Easy Run Mode

## First Time Setup (Only Once)

```bash
# Make scripts executable
chmod +x run.sh stop.sh

# Install dependencies (if not done already)
cd backend
pip install -r requirements.txt --break-system-packages
cd ..

cd frontend
npm install
cd ..
```

## Daily Use

### Start Everything (One Command!)

```bash
./run.sh
```

This will:
- ✅ Start backend on http://localhost:8000
- ✅ Start frontend on http://localhost:5173
- ✅ Open your browser automatically
- ✅ Show logs in terminal

**When you see:** `➜ Local: http://localhost:5173/`
→ Open that link in your browser!

### Stop Everything

Press `Ctrl+C` in the terminal (stops both automatically)

Or run:
```bash
./stop.sh
```

## Logs

Backend logs are saved to: `backend.log`

If something goes wrong, check:
```bash
tail -f backend.log
```

## Troubleshooting

**"Permission denied" error:**
```bash
chmod +x run.sh stop.sh
```

**Port already in use:**
```bash
./stop.sh
# Wait 2 seconds
./run.sh
```

**Backend won't start:**
```bash
cd backend
source venv/bin/activate
python main.py
# See error message directly
```

**Frontend won't start:**
```bash
cd frontend
npm run dev
# See error message directly
```

## What's Running?

Check what's running:
```bash
# Backend
curl http://localhost:8000/health

# Frontend  
curl http://localhost:5173
```

## Manual Mode (If Script Doesn't Work)

**Terminal 1:**
```bash
cd backend
source venv/bin/activate
python main.py
```

**Terminal 2:**
```bash
cd frontend
npm run dev
```

---

**That's it!** Just run `./run.sh` and you're good to go. 🚀
