<script>
  import { createEventDispatcher } from 'svelte';
  
  export let slots = [];
  export let tasks = [];
  export let projects = [];
  
  const dispatch = createEventDispatcher();
  
  let currentMonth = new Date();
  
  $: monthStart = getMonthStart(currentMonth);
  $: monthEnd = getMonthEnd(currentMonth);
  $: calendarDays = generateCalendarDays(currentMonth);
  
  function getMonthStart(date) {
    return new Date(date.getFullYear(), date.getMonth(), 1);
  }
  
  function getMonthEnd(date) {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0);
  }
  
  function generateCalendarDays(date) {
    const year = date.getFullYear();
    const month = date.getMonth();
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    // Get day of week (0 = Sunday, 1 = Monday, etc)
    let startDay = firstDay.getDay();
    // Convert to Monday = 0
    startDay = startDay === 0 ? 6 : startDay - 1;
    
    const days = [];
    
    // Add previous month days
    const prevMonthDays = startDay;
    const prevMonth = new Date(year, month, 0);
    for (let i = prevMonthDays; i > 0; i--) {
      const day = new Date(year, month - 1, prevMonth.getDate() - i + 1);
      days.push({ date: day, isCurrentMonth: false });
    }
    
    // Add current month days
    for (let i = 1; i <= lastDay.getDate(); i++) {
      const day = new Date(year, month, i);
      days.push({ date: day, isCurrentMonth: true });
    }
    
    // Add next month days to complete the grid
    const remainingDays = 42 - days.length; // 6 weeks * 7 days
    for (let i = 1; i <= remainingDays; i++) {
      const day = new Date(year, month + 1, i);
      days.push({ date: day, isCurrentMonth: false });
    }
    
    return days;
  }
  
  function getSlotsForDay(date) {
    const dayStart = new Date(date);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(date);
    dayEnd.setHours(23, 59, 59, 999);
    
    return slots.filter(slot => {
      const slotStart = new Date(slot.start_datetime);
      return slotStart >= dayStart && slotStart <= dayEnd;
    });
  }
  
  function getTaskForSlot(slot) {
    return tasks.find(t => t.id === slot.task_id);
  }
  
  function getProjectForTask(task) {
    if (!task || !task.project_id) return null;
    return projects.find(p => p.id === task.project_id);
  }
  
  function isToday(date) {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  }
  
  function previousMonth() {
    currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1);
    dispatch('dateChange', { month: currentMonth });
  }
  
  function nextMonth() {
    currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);
    dispatch('dateChange', { month: currentMonth });
  }
  
  function goToToday() {
    currentMonth = new Date();
    dispatch('dateChange', { month: currentMonth });
  }
  
  function formatMonthYear() {
    return currentMonth.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
  }
  
  function handleSlotClick(slot) {
    dispatch('slotClick', slot);
  }
</script>

<div class="month-view">
  <!-- Month Navigation -->
  <div class="month-header">
    <div class="month-nav">
      <button class="btn btn-sm btn-secondary" on:click={previousMonth}>
        ← Prev
      </button>
      <h2 class="month-title">{formatMonthYear()}</h2>
      <button class="btn btn-sm btn-secondary" on:click={nextMonth}>
        Next →
      </button>
    </div>
    <button class="btn btn-sm btn-primary" on:click={goToToday}>
      Today
    </button>
  </div>
  
  <!-- Day Headers -->
  <div class="calendar-grid">
    {#each ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as dayName}
      <div class="day-header">{dayName}</div>
    {/each}
    
    <!-- Calendar Days -->
    {#each calendarDays as { date, isCurrentMonth }}
      {@const daySlots = getSlotsForDay(date)}
      {@const isToday_ = isToday(date)}
      
      <div 
        class="day-cell"
        class:other-month={!isCurrentMonth}
        class:today={isToday_}
      >
        <div class="day-number" class:today-number={isToday_}>
          {date.getDate()}
        </div>
        
        <div class="day-slots-container">
          {#each daySlots.slice(0, 3) as slot}
            {@const task = getTaskForSlot(slot)}
            {@const project = getProjectForTask(task)}
            
            {#if task}
              <div 
                class="mini-slot"
                class:completed={slot.completed}
                style="background-color: {project ? project.colour + '20' : '#e5e7eb'}; border-left: 3px solid {project ? project.colour : '#9ca3af'};"
                on:click={() => handleSlotClick(slot)}
                title="{task.title} ({new Date(slot.start_datetime).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })})"
              >
                <div class="mini-slot-time">
                  {new Date(slot.start_datetime).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                </div>
                <div class="mini-slot-title">
                  {task.title}
                </div>
              </div>
            {/if}
          {/each}
          
          {#if daySlots.length > 3}
            <div class="more-slots">
              +{daySlots.length - 3} more
            </div>
          {/if}
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .month-view {
    width: 100%;
    max-width: 1400px;
    margin: 0 auto;
  }
  
  .month-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding: 16px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
  
  .month-nav {
    display: flex;
    align-items: center;
    gap: 20px;
  }
  
  .month-title {
    font-size: 24px;
    font-weight: 600;
    margin: 0;
    min-width: 200px;
    text-align: center;
  }
  
  .calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 1px;
    background: #e5e7eb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
  }
  
  .day-header {
    background: #f9fafb;
    padding: 12px;
    text-align: center;
    font-weight: 600;
    font-size: 14px;
    color: #6b7280;
    text-transform: uppercase;
  }
  
  .day-cell {
    background: white;
    min-height: 120px;
    padding: 8px;
    position: relative;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  .day-cell:hover {
    background: #f9fafb;
  }
  
  .day-cell.other-month {
    background: #f9fafb;
    opacity: 0.5;
  }
  
  .day-cell.today {
    background: #eff6ff;
  }
  
  .day-number {
    font-size: 14px;
    font-weight: 500;
    color: #4b5563;
    margin-bottom: 8px;
  }
  
  .day-number.today-number {
    background: #3b82f6;
    color: white;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
  }
  
  .day-slots-container {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .mini-slot {
    padding: 4px 6px;
    border-radius: 4px;
    font-size: 11px;
    cursor: pointer;
    transition: transform 0.1s;
  }
  
  .mini-slot:hover {
    transform: translateX(2px);
  }
  
  .mini-slot.completed {
    opacity: 0.6;
    text-decoration: line-through;
  }
  
  .mini-slot-time {
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 2px;
  }
  
  .mini-slot-title {
    color: #1f2937;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .more-slots {
    font-size: 11px;
    color: #6b7280;
    font-weight: 500;
    padding: 2px 6px;
    text-align: center;
  }
</style>
