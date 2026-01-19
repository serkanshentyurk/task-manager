# PhD Task Manager - Complete Application

A full-stack task management application with intelligent auto-scheduling, built for PhD research workflow.

## 🎉 What You Have Now

**Backend (FastAPI)** ✅ Complete & Tested
- Smart auto-scheduling algorithm
- Priority-based task bumping
- Recurring patterns (weekly/daily)
- Blocked times (meetings, lunch)
- Calendar settings
- REST API with 30+ endpoints

**Frontend (Svelte)** ✅ Just Built
- Visual calendar (week view)
- Task list sidebar
- Create/edit tasks with form
- Dashboard with stats
- One-click auto-schedule
- Responsive design

## Quick Start

### 1. Start the Backend

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python main.py
```

Backend runs on: **http://localhost:8000**

### 2. Start the Frontend

Open a NEW terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on: **http://localhost:5173**

### 3. Open in Browser

Visit: **http://localhost:5173**

You should see the dashboard!

## Project Structure

```
phd-task-manager/
├── backend/              ✅ FastAPI
│   ├── main.py          # API endpoints
│   ├── database.py      # SQLite operations
│   ├── models.py        # Data validation
│   ├── scheduling.py    # Smart scheduling
│   ├── rrule_utils.py   # Recurring patterns
│   └── email_reminders.py
│
├── frontend/            ✅ Svelte
│   ├── src/
│   │   ├── App.svelte         # Main app
│   │   ├── api.js             # Backend API client
│   │   ├── global.css         # Styles
│   │   └── components/
│   │       ├── Calendar.svelte    # Week view calendar
│   │       ├── TaskList.svelte    # Sidebar task list
│   │       ├── TaskForm.svelte    # Create/edit modal
│   │       └── Dashboard.svelte   # Stats overview
│   ├── index.html
│   └── package.json
│
└── data/
    └── tasks.db         # SQLite database (auto-created)
```

## Using the Application

### Create a Task

1. Click **"+ New Task"** button
2. Fill in:
   - Title (required)
   - Priority (1-5)
   - Estimated hours
   - Start date (required)
   - Deadline
   - Project (optional)
3. Check **"Auto-schedule this task"** to automatically find time slots
4. Check **"Force bump"** if it's high priority and should bump others
5. Click **"Create"**

### View Your Schedule

- Calendar shows all scheduled slots
- Color-coded by priority:
  - Gray = Priority 1
  - Blue = Priority 2
  - Yellow = Priority 3
  - Orange = Priority 4
  - Red = Priority 5 (Critical)
- Click on a slot to mark it complete or edit the task

### Auto-Schedule Multiple Tasks

Click the **"⚡ Auto-Schedule"** button in the header to automatically schedule all unscheduled tasks.

### Complete a Task

- Click the task in the sidebar
- Click **"✓ Complete"** button
- Future slots are automatically deleted

### Navigate Calendar

- **← Prev / Next →**: Move week by week
- **Today**: Jump to current week

## Features

### ✅ What Works Now

**Task Management:**
- Create/edit/delete tasks
- Set priority (1-5)
- Set deadlines and start dates
- Assign to projects
- Mark tasks complete

**Smart Scheduling:**
- Auto-schedule finds best time slots
- Splits long tasks into sessions (max 4h each)
- Respects calendar settings (work hours)
- Avoids conflicts

**Calendar:**
- Week view visualization
- Color-coded by priority
- Click slots to interact
- Navigate weeks easily

**Dashboard:**
- Task counts by status
- High priority task count
- Upcoming deadlines (next 7 days)

### 🚧 What's Not Built Yet

- Recurring task UI (API works, needs form)
- Blocked times UI (API works, needs form)
- "Reallocate now" button
- Drag-and-drop to reschedule
- Month view
- Project management UI
- Settings panel
- Email reminder UI

## Configuration

### Work Hours

Currently hardcoded to:
- **Weekdays**: Monday-Friday
- **Hours**: 9:00 AM - 5:00 PM

To change, edit via API:
```bash
curl -X PATCH http://localhost:8000/settings/calendar \
  -H "Content-Type: application/json" \
  -d '{
    "work_start_time": "10:00",
    "work_end_time": "18:00"
  }'
```

### Task Defaults

- **Min session**: 2 hours
- **Max session**: 4 hours
- **Default priority**: 3 (Medium)

## Troubleshooting

**"Failed to load data" error**
- Check backend is running on port 8000
- Open http://localhost:8000 in browser - should see API info

**Calendar shows no slots**
- Create a task with auto-schedule enabled
- Make sure start_date is filled in
- Check work hours are configured

**npm install fails**
- Try: `npm install --legacy-peer-deps`
- Make sure Node.js 16+ is installed

**Port already in use**
- Backend: Change port in `main.py` (line: `uvicorn.run(app, port=8000)`)
- Frontend: Change port in `vite.config.js`

## Development Tips

### Backend API Docs

Visit http://localhost:8000/docs for interactive API documentation.

### Hot Reload

Both backend and frontend have hot reload:
- **Backend**: Auto-reloads when you save .py files
- **Frontend**: Auto-reloads when you save .svelte files

### Testing

```bash
# Backend - see backend/README.md for curl tests

# Frontend - run in dev mode and check browser console
npm run dev
```

### Building for Production

```bash
# Frontend
cd frontend
npm run build
# Creates dist/ folder with optimized files

# Backend - already production ready
# Just needs uvicorn with more workers
```

## Next Steps

### Option 1: Add More Features

**Easy additions:**
- Blocked times UI (add a modal form)
- Recurring tasks UI (add pattern selector)
- Settings panel (work hours, excluded dates)
- Project creation UI

**Medium complexity:**
- Drag-and-drop to reschedule slots
- Month view calendar
- "Reallocate now" feature
- Task filtering by project

**Advanced:**
- Undo/redo system
- Email reminders (schedule background jobs)
- Docker deployment
- Multi-user support

### Option 2: Use As-Is

The core workflow works perfectly:
1. Create tasks
2. Auto-schedule
3. View calendar
4. Mark complete

This is enough for daily use!

### Option 3: Customize for Your Workflow

The code is modular and well-commented. Easy to:
- Change colors/styling (global.css)
- Add custom task fields (models.py + TaskForm.svelte)
- Modify scheduling algorithm (scheduling.py)
- Add your own components

## Support

If something doesn't work:
1. Check both backend and frontend are running
2. Check browser console for errors (F12)
3. Check backend terminal for errors
4. Try deleting `data/tasks.db` and restarting (fresh database)

## Architecture

**Backend:**
- FastAPI (modern Python web framework)
- SQLite (simple, file-based database)
- No authentication (single-user)

**Frontend:**
- Svelte (reactive, fast framework)
- Vite (fast build tool)
- Vanilla CSS (no Tailwind compilation needed)

**Communication:**
- REST API over HTTP
- JSON data format
- CORS enabled for local development

## Files You Can Safely Edit

**Styling:**
- `frontend/src/global.css` - All visual styles

**Components:**
- `frontend/src/components/*.svelte` - All UI components

**API:**
- `backend/main.py` - Add new endpoints here

**Database:**
- `backend/database.py` - Modify schema
- Delete `data/tasks.db` to reset

**Scheduling:**
- `backend/scheduling.py` - Modify algorithm
---

**Enjoy your new task manager!** 🎉
