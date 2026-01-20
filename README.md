# Task Manager

A comprehensive task management application specifically designed for PhD students and researchers. Built to handle the complex, flexible scheduling demands of academic research with smart auto-scheduling, recurring tasks, project organisation, and both weekly and monthly calendar views.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
[![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg

---

## Overview

Task Manager helps you organise your research workflow with:
- **Smart Auto-Scheduling** - Automatically allocate tasks based on deadlines, priorities, and your availability
- **Recurring Tasks** - Weekly meetings, daily data collection, regular lab work
- **Project Organisation** - Group tasks by research area (imaging study, modelling, literature review, teaching)
- **Flexible Calendar Views** - Week view for daily planning, month view for long-term overview
- **Conflict Detection** - Intelligent slot management with swap and reschedule options
- **Fill Empty Slots** - Use unexpected free time by pulling future tasks forward
- **Customisable Settings** - Configure work hours, lunch breaks, and blocked times

Perfect for managing the complex, non-linear nature of PhD research work.

---

## Features

### Core Task Management
- ✅ Create tasks with priorities (P1-P5), deadlines, and estimated hours
- ✅ Minimum session duration to avoid fragmented work
- ✅ Task descriptions and notes
- ✅ Task completion tracking
- ✅ Mark tasks as reschedulable or fixed

### Smart Scheduling
- ⚡ **Auto-Schedule** - Automatically allocate unscheduled tasks
- 🔄 **Recurring Tasks** - Daily, weekly, or monthly patterns with flexible end dates
- 📅 **Manual Slots** - Create fixed time slots for specific commitments
- 🎯 **Priority-Based** - Higher priority tasks scheduled earlier
- ⏰ **Deadline-Aware** - Tasks due soon get scheduled first

### Calendar Views
- **Week View** - Detailed 7-day view with drag-and-drop rescheduling
- **Month View** - 6-week calendar grid for long-term planning
- **Time Slots** - Visual representation with project colour coding
- **Completed Tracking** - See what you've accomplished

### Project Organisation
- 📁 **Multiple Projects** - Organise tasks by research area
- 🎨 **Colour Coding** - Visual distinction with 8 colours
- 📊 **Project Stats** - Track hours, completion %, and progress per project
- 📋 **Task Lists** - View all tasks within each project

### Advanced Features
- 🔍 **Fill Empty Slots** - Click empty time to see suggestions from future tasks
- ⚠️ **Sanity Checks** - Automatic detection of scheduling mismatches
- 🔒 **Fixed Slots** - Lock important commitments to prevent rescheduling
- 🔄 **Swap Functionality** - Intelligent slot swapping with conflict resolution
- ⚙️ **Settings Panel** - Configure work hours, schedule, lunch breaks, blocked times

### Data & Stats
- 📈 **Dashboard** - Overview of tasks, hours, and completion rates
- 🎯 **Weekly Progress** - Track what's scheduled vs completed
- 📊 **Project Breakdown** - Hours and completion by project

---

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- npm or yarn

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd phd-task-manager
```

2. **Set up the backend**
```bash
cd backend
pip install -r requirements.txt
```

3. **Set up the frontend**
```bash
cd frontend
npm install
```

4. **Run the application**
```bash
# From project root
./run.sh
```

The app will open automatically at `http://localhost:3000`

- Backend runs on `http://localhost:8000`
- Frontend runs on `http://localhost:3000`

### Stopping the Application
```bash
./stop.sh
```

---

## User Guide

### Getting Started

#### 1. Configure Your Settings (Recommended First Step)
Click the ⚙️ **Settings** button (top-right) to configure:

**Work Hours:**
- Set your typical work day (e.g., 9:00 - 18:00)
- Choose work schedule (Weekdays, All Week, or Custom Days)

**Lunch Break:**
- Enable/disable lunch break
- Set start time and duration (e.g., 12:00, 1 hour)

**Blocked Times:**
- Add recurring commitments (teaching, meetings, seminars)
- System will avoid scheduling tasks during blocked times

#### 2. Create Projects
Navigate to the **📁 Projects** tab to organise your work:

1. Click **"+ New Project"**
2. Enter project name (e.g., "Imaging Study", "Literature Review", "Teaching")
3. Choose a colour for visual distinction
4. Click **"Create Project"**

**Project Features:**
- View all tasks within a project
- See completion progress and hours breakdown
- Track active vs completed tasks
- Delete projects (tasks remain, just unassigned)

#### 3. Create Tasks

Click **"+ New Task"** to create a task:

**Basic Information:**
- **Title** - What needs to be done
- **Description** - Optional details
- **Project** - Which research area this belongs to
- **Priority** - P1 (urgent) to P5 (low priority)

**Scheduling:**
- **Estimated Hours** - Total time needed
- **Min Session Hours** - Minimum work session length (avoids fragmentation)
- **Start Date** - When you can start working on this
- **Deadline** - When it must be completed
- **Allow Rescheduling** - Whether auto-scheduler can move this task

**Auto-Schedule vs Manual Slots:**
- **Auto-Schedule** (default) - Let the system find optimal times
- **Manual Slots** - Specify exact time slots yourself

#### 4. Recurring Tasks

For tasks that repeat (meetings, data collection, regular lab work):

1. Check **"🔁 Make this a recurring task"**
2. Configure recurrence:
   - **Frequency** - Daily, Weekly, or Monthly
   - **Interval** - Every X days/weeks/months
   - **Days** - (Weekly only) Select specific days (Mon, Tue, etc.)
   - **End Date** - Optional, leave empty for ongoing

**Examples:**
```
Weekly Lab Meeting:
- Frequency: Weekly
- Every: 1 week
- Days: Monday
- Duration: 2 hours

Daily Data Collection:
- Frequency: Daily
- Every: 1 day
- End Date: End of semester
```

### Calendar Management

#### Week View (Default)
- **Drag & Drop** - Click and drag slots to reschedule
- **Click Slot** - View task details, complete, reschedule, or delete
- **Click Empty Space** - See suggestions for tasks you can pull forward
- **Navigation** - Use arrow buttons to move between weeks

#### Month View
- Click **📆 Month** button (above calendar)
- **Overview** - See all scheduled work for the month
- **Mini Cards** - Up to 3 tasks shown per day, "+X more" if more slots
- **Click Slots** - View/edit task details
- **Navigation** - Move between months, jump to "Today"
- **Switch Back** - Click **📅 Week** for detailed view

#### Slot Actions

When you click a time slot:

**Three-Button Modal:**
- **✓ Complete** - Mark this time slot as done
- **🔄 Reschedule** - Choose new time (checks for conflicts)
- **✖️ Delete** - Remove this time slot

**After Reschedule:**
If there's a conflict, you'll see:
- **🔄 Swap Both Events** - Exchange times with conflicting slot
- **✖️ Cancel Move** - Keep original time

#### Fill Empty Slots

Click on empty calendar space to:
1. System calculates available time
2. Shows suggestions from future tasks that fit
3. Sorted by priority, deadline, and distance in future
4. Click suggestion to move task to this time

**Perfect for:**
- Meeting cancelled, have free time
- Finished early, want to start next task
- Unexpected gap in schedule

### Project Management

In the **📁 Projects** tab:

**Project Cards Show:**
- Progress bar with completion %
- Total hours, completed hours, scheduled hours, remaining hours
- Active vs completed task counts
- List of tasks (first 5 shown, "+X more" if more)

**Actions:**
- Click **🗑️** to delete project (tasks remain, just unassigned)
- Click task cards to edit tasks
- Create new projects with **"+ New Project"**

### Advanced Features

#### Sanity Check System
Automatically detects when scheduled hours don't match estimated hours:

- **Yellow Banner** - Shown when mismatches detected
- **Task Warnings** - "⚠️ Over-scheduled by 2h" on problem tasks
- **Fix Options:**
  - **Reschedule** - Delete incomplete slots and auto-schedule correctly
  - **Update Estimate** - Change estimated hours to match current schedule

#### Auto-Schedule Button
Click **⚡ Auto-Schedule** to:
1. Find all unscheduled tasks
2. Sort by priority and deadline
3. Allocate to available time slots
4. Respect work hours, lunch breaks, and blocked times

**Smart Features:**
- Won't overlap with existing slots
- Respects minimum session duration
- Avoids blocked times
- Considers task dependencies (start date, deadline)

#### Settings Panel
Access via ⚙️ button (top-right):

**Work Hours:**
- Dropdown menus for start/end times
- Default: 09:00 - 18:00

**Work Schedule:**
- Weekdays (Mon-Fri)
- All Week (Mon-Sun)
- Custom Days (select specific days)

**Lunch Break:**
- Toggle on/off
- Time picker for start time
- Duration slider (0.5-3 hours)

**Blocked Times:**
- Add title, start datetime, end datetime
- Examples: Teaching sessions, lab days, seminars
- Delete unwanted blocks
- View all blocked times

---

## Technical Architecture

### Backend (Python/FastAPI)
```
backend/
├── main.py              # API endpoints
├── database.py          # SQLite operations
├── models.py            # Pydantic models
├── scheduling.py        # Auto-scheduling logic
├── rrule_utils.py       # Recurring task handling
└── requirements.txt     # Python dependencies
```

**Key Technologies:**
- FastAPI - Modern, fast web framework
- SQLite - Embedded database
- Pydantic - Data validation
- python-dateutil - Recurrence rules (rrule)

**API Endpoints:**
- `/tasks` - CRUD operations for tasks
- `/projects` - Project management
- `/slots` - Time slot management
- `/schedule/auto` - Auto-scheduling
- `/time-allocations` - Recurring tasks
- `/blocked-times` - Blocked time management
- `/settings/calendar` - Calendar configuration
- `/stats/overview` - Dashboard statistics

### Frontend (Svelte)
```
frontend/src/
├── App.svelte           # Main application
├── api.js               # Backend API client
├── components/
│   ├── Calendar.svelte          # Week view
│   ├── MonthView.svelte         # Month view
│   ├── TaskList.svelte          # Task sidebar
│   ├── TaskForm.svelte          # Create/edit tasks
│   ├── ProjectsView.svelte      # Project management
│   ├── Dashboard.svelte         # Stats overview
│   ├── SettingsModal.svelte     # Settings panel
│   ├── SlotActionModal.svelte   # Slot actions
│   ├── FillSlotModal.svelte     # Fill empty slots
│   ├── ConflictResolutionModal.svelte  # Conflict handling
│   └── RescheduleSlotModal.svelte      # Rescheduling
└── global.css           # Styling
```

**Key Technologies:**
- Svelte - Reactive UI framework
- Vite - Build tool and dev server
- Native JavaScript - No heavy dependencies

### Database Schema

**Tables:**
- `tasks` - Task information (title, priority, deadline, estimated hours, etc.)
- `projects` - Project groupings (name, colour)
- `scheduled_slots` - Calendar time slots (start, end, task_id, completed, is_fixed)
- `time_allocations` - Recurring task patterns (rrule, duration)
- `blocked_times` - Unavailable time periods (teaching, meetings)
- `calendar_settings` - User preferences (work hours, schedule, lunch)

---

## Customisation

### Changing Colours
Project colours in `ProjectsView.svelte`:
```javascript
const colors = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
];
```

### Work Hours
Default work hours in `backend/database.py`:
```python
work_start_hour: 9
work_end_hour: 18
```

### Auto-Schedule Algorithm
Modify scheduling logic in `backend/scheduling.py`:
- `find_next_available_slot()` - Slot finding logic
- `auto_schedule_tasks()` - Main scheduling algorithm
- Priority weights, deadline urgency calculations

---

## Development

### Project Structure
```
phd-task-manager/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── scheduling.py
│   ├── rrule_utils.py
│   ├── requirements.txt
│   └── tasks.db          # SQLite database
├── frontend/
│   ├── src/
│   │   ├── App.svelte
│   │   ├── api.js
│   │   ├── components/
│   │   └── global.css
│   ├── public/
│   ├── package.json
│   └── vite.config.js
├── run.sh                # Start script
├── stop.sh               # Stop script
└── README.md
```

### Running in Development

**Backend only:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Frontend only:**
```bash
cd frontend
npm run dev
```

**Both (recommended):**
```bash
./run.sh
```

### API Documentation
Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Database Management

**View database:**
```bash
cd backend
sqlite3 tasks.db
.tables
SELECT * FROM tasks;
.quit
```

**Reset database:**
```bash
cd backend
rm tasks.db
# Restart app - database will reinitialize
```

**Backup database:**
```bash
cp backend/tasks.db backend/tasks.backup.db
```

---

## 📊 Usage Examples

### Typical PhD Workflow

**Monday Morning:**
1. Open app, view week view
2. Check today's tasks
3. Mark weekend tasks as complete
4. Drag Tuesday's task to fill Monday afternoon gap
5. Add new urgent task with P1 priority
6. Click "Auto-Schedule" to fit it in

**Mid-Week:**
1. Lab meeting cancelled (2 hours free)
2. Click empty slot
3. See suggestions: "Data analysis" (2h, scheduled for Friday)
4. Click to move - now have extra Friday afternoon free

**End of Week:**
1. Switch to month view
2. Review next week's schedule
3. Notice deadline on 31st
4. Create tasks needed for deadline
5. Auto-schedule allocates them appropriately

**Monthly Planning:**
1. Projects tab - review all projects
2. See "Imaging Study" is 65% complete
3. Check month view for upcoming deadlines
4. Add recurring "Weekly Progress Meeting"
5. Block out conference dates

---

## Troubleshooting

### App Won't Start
```bash
# Check Python version
python3 --version  # Should be 3.9+

# Check Node version
node --version  # Should be 16+

# Reinstall dependencies
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use stop script
./stop.sh
```

### Database Errors
```bash
# Reset database
rm backend/tasks.db
# Restart app
```

### Auto-Schedule Not Working
- Check Settings: Ensure work hours are configured
- Check Tasks: Verify start_date is set
- Check Availability: Ensure there are available time slots
- Check Constraints: Look for conflicting blocked times

### Slots Not Appearing on Calendar
- Check date range: Ensure slots are within visible week/month
- Check task status: Completed tasks show differently
- Refresh data: Reload the page

---

## 🚀 Deployment

### Option 1: Free Hosting (Vercel + Railway)

**Frontend (Vercel):**
```bash
cd frontend
npm run build
vercel deploy
```

**Backend (Railway):**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

**Environment Variables:**
Set in Railway dashboard:
- `PORT=8000`
- `DATABASE_URL` (if using PostgreSQL instead of SQLite)

### Option 2: DigitalOcean Droplet

**1. Create Droplet:**
- Ubuntu 22.04
- $6/month plan
- Add SSH key

**2. Setup Server:**
```bash
# SSH into server
ssh root@your_droplet_ip

# Install dependencies
apt update
apt install python3-pip nodejs npm nginx

# Clone repo
git clone <your-repo> /var/www/phd-task-manager
```

**3. Configure Nginx:**
```nginx
# /etc/nginx/sites-available/phd-task-manager
server {
    listen 80;
    server_name your_domain.com;
    
    location / {
        proxy_pass http://localhost:3000;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

**4. Run with systemd:**
Create service files for backend and frontend to run on startup.

### Option 3: University Server
If your department provides server access:
1. Request hosting for web application
2. Deploy backend and frontend
3. Use department domain (e.g., yourphd.university.ac.uk)

---

## Security Considerations

**Current State (Development):**
- No authentication
- No authorisation
- SQLite database (single-user)
- Local network only

**For Production/Multi-User:**
- Add user authentication (e.g., JWT tokens)
- Add user-specific data isolation
- Migrate to PostgreSQL/MySQL
- Add HTTPS (Let's Encrypt)
- Add CORS configuration
- Add rate limiting
- Add input sanitisation
- Add SQL injection protection (use parameterized queries - already done)

---

## Future Enhancements

### Planned Features
- [ ] Email reminders for upcoming deadlines
- [ ] Export to calendar (iCal format)
- [ ] Task templates (common research tasks)
- [ ] Collaboration features (share tasks with supervisor)
- [ ] Time tracking (actual vs estimated hours)
- [ ] Gantt chart view
- [ ] Mobile-responsive improvements
- [ ] Progressive Web App (PWA) support
- [ ] Dark mode
- [ ] Keyboard shortcuts

### Ideas Welcome!
Open an issue on GitHub with feature requests or suggestions.

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- **Backend:** Follow PEP 8 (Python)
- **Frontend:** Use Prettier for formatting
- **Commits:** Use conventional commits format

---

## 📄 License

This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg
---

**Technologies:**
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Svelte](https://svelte.dev/) - Frontend framework
- [SQLite](https://www.sqlite.org/) - Database
- [python-dateutil](https://dateutil.readthedocs.io/) - Recurrence rules

---

## Support

For questions, issues, or suggestions:
- Open an issue on GitHub
- Email: serkan[dot]shentyurk[dot]24[at]ucl[dot]ac[dot]uk
- Documentation: See this README

---


**Last Updated:** January 2026
**Version:** 1.0.0
**Status:** Production Ready
