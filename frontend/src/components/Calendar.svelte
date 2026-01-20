<script>
  import { createEventDispatcher } from 'svelte';

  export let slots = [];
  export let tasks = [];
  export let startDate;
  export let endDate;

  const dispatch = createEventDispatcher();

  let viewMode = 'week'; // 'week' or 'month'
  
  // Drag and drop state
  let draggingSlot = null;
  let dragOverDay = null;
  let dragOverY = null;

  // Use startDate from props directly
  $: currentWeekStart = getWeekStart(startDate || new Date());

  function getWeekStart(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust to Monday
    return new Date(d.setDate(diff));
  }

  function getWeekDays(weekStart) {
    const days = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(weekStart);
      date.setDate(weekStart.getDate() + i);
      days.push(date);
    }
    return days;
  }

  function formatDateHeader(date) {
    return date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  function formatTime(datetime) {
    return new Date(datetime).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  }

  function getSlotsForDay(date) {
    const dateStr = date.toISOString().split('T')[0];
    return slots.filter(slot => {
      const slotDate = slot.start_datetime.split('T')[0];
      return slotDate === dateStr;
    }).sort((a, b) => a.start_datetime.localeCompare(b.start_datetime));
  }

  function getTaskForSlot(slot) {
    return tasks.find(t => t.id === slot.task_id);
  }

  function getSlotColor(slot) {
    const task = getTaskForSlot(slot);
    if (!task) return '#94a3b8';
    
    // Color by priority
    const colors = {
      1: '#94a3b8',
      2: '#60a5fa',
      3: '#fbbf24',
      4: '#fb923c',
      5: '#ef4444'
    };
    return colors[task.priority] || '#60a5fa';
  }

  function getSlotHeight(slot) {
    const start = new Date(slot.start_datetime);
    const end = new Date(slot.end_datetime);
    const hours = (end - start) / (1000 * 60 * 60);
    return Math.max(hours * 60, 40); // 60px per hour, minimum 40px
  }

  function getSlotTop(slot) {
    const time = new Date(slot.start_datetime);
    const hours = time.getHours();
    const minutes = time.getMinutes();
    return (hours - 9) * 60 + minutes; // Assuming 9am start
  }

  function handleSlotClick(slot) {
    dispatch('slotClick', slot);
  }

  // Drag and drop handlers
  function handleDragStart(event, slot) {
    draggingSlot = slot;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', slot.id);
    event.target.style.opacity = '0.5';
  }

  function handleDragEnd(event) {
    event.target.style.opacity = '1';
    draggingSlot = null;
    dragOverDay = null;
    dragOverY = null;
  }

  function handleDragOver(event, day) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    
    // Get the calendar column element
    const dayColumn = event.currentTarget;
    const rect = dayColumn.getBoundingClientRect();
    const y = event.clientY - rect.top;
    
    dragOverDay = day;
    dragOverY = y;
  }

  function handleDrop(event, day) {
    event.preventDefault();
    
    console.log('Drop event triggered', { draggingSlot, day });
    
    if (!draggingSlot) {
      console.log('No dragging slot, returning');
      return;
    }
    
    // event.currentTarget is already the .day-slots div
    const daySlots = event.currentTarget;
    const rect = daySlots.getBoundingClientRect();
    const y = event.clientY - rect.top;
    
    // Convert pixel position to time (60px per hour, starting at 9am)
    const hours = Math.floor(y / 60) + 9;
    const minutes = Math.round(((y % 60) / 60) * 60 / 15) * 15; // Round to 15 min intervals
    
    // Create new start time
    const newStart = new Date(day);
    newStart.setHours(hours, minutes, 0, 0);
    
    console.log('Calculated new time:', {
      hours,
      minutes,
      newStart: newStart.toISOString(),
      originalSlot: draggingSlot
    });
    
    // Dispatch move event
    dispatch('slotMove', {
      slot: draggingSlot,
      newStart: newStart.toISOString()
    });
    
    console.log('Dispatched slotMove event');
    
    draggingSlot = null;
    dragOverDay = null;
    dragOverY = null;
  }

  function handleEmptySlotClick(event, day) {
    // Only trigger if clicking directly on day-slots or hour-block (empty space)
    const target = event.target;
    if (!target.classList.contains('day-slots') && !target.classList.contains('hour-block')) {
      return; // Clicked on a slot, not empty space
    }
    
    const daySlots = event.currentTarget;
    const rect = daySlots.getBoundingClientRect();
    const y = event.clientY - rect.top;
    
    // Calculate time from click position
    const pixelsPerHour = 60;
    const hours = Math.floor(y / pixelsPerHour) + 9;
    const minutes = Math.round(((y % 60) / 60) * 60 / 15) * 15;
    
    // Create start time
    const clickTime = new Date(day);
    clickTime.setHours(hours, minutes, 0, 0);
    
    // Find next slot or end of day for end time
    const daySlotsForDay = getSlotsForDay(day);
    let endTime = new Date(clickTime);
    endTime.setHours(18, 0, 0, 0); // Default to end of work day
    
    // Find next slot after click time
    for (const slot of daySlotsForDay) {
      const slotStart = new Date(slot.start_datetime);
      if (slotStart > clickTime) {
        endTime = slotStart;
        break;
      }
    }
    
    // Minimum 30 min slot
    if ((endTime - clickTime) / (1000 * 60) < 30) {
      endTime = new Date(clickTime.getTime() + 30 * 60 * 1000);
    }
    
    console.log('Empty slot clicked:', { clickTime, endTime });
    
    dispatch('emptySlotClick', {
      startTime: clickTime.toISOString(),
      endTime: endTime.toISOString()
    });
  }

  function previousWeek() {
    const newStart = new Date(currentWeekStart);
    newStart.setDate(newStart.getDate() - 7);
    
    const newEnd = new Date(newStart);
    newEnd.setDate(newEnd.getDate() + 6);
    
    dispatch('dateChange', {
      start: newStart,
      end: newEnd
    });
  }

  function nextWeek() {
    const newStart = new Date(currentWeekStart);
    newStart.setDate(newStart.getDate() + 7);
    
    const newEnd = new Date(newStart);
    newEnd.setDate(newEnd.getDate() + 6);
    
    dispatch('dateChange', {
      start: newStart,
      end: newEnd
    });
  }

  function today() {
    const newStart = getWeekStart(new Date());
    const newEnd = new Date(newStart);
    newEnd.setDate(newStart.getDate() + 6);
    
    dispatch('dateChange', {
      start: newStart,
      end: newEnd
    });
  }

  $: weekDays = getWeekDays(currentWeekStart);
  $: isToday = (date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };
</script>

<div class="calendar-wrapper">
  <div class="flex items-center justify-between mb-4">
    <div class="flex gap-2">
      <button class="btn btn-sm btn-secondary" on:click={previousWeek}>
        ← Prev
      </button>
      <button class="btn btn-sm btn-secondary" on:click={today}>
        Today
      </button>
      <button class="btn btn-sm btn-secondary" on:click={nextWeek}>
        Next →
      </button>
    </div>
    
    <div style="font-size: 18px; font-weight: 600;">
      {currentWeekStart.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}
    </div>
  </div>

  <div class="calendar-grid">
    <div class="time-column">
      <div class="time-header"></div>
      {#each Array(9) as _, hour}
        <div class="time-label">
          {(9 + hour).toString().padStart(2, '0')}:00
        </div>
      {/each}
    </div>

    {#each weekDays as day}
      <div class="day-column">
        <div class="day-header" class:today={isToday(day)}>
          {formatDateHeader(day)}
        </div>
        <div 
          class="day-slots"
          on:click={(e) => handleEmptySlotClick(e, day)}
          on:dragover={(e) => handleDragOver(e, day)}
          on:drop={(e) => handleDrop(e, day)}
        >
          {#each Array(9) as _, hour}
            <div class="hour-block"></div>
          {/each}
          
          {#each getSlotsForDay(day) as slot}
            {@const task = getTaskForSlot(slot)}
            {@const isFixed = slot.is_fixed || false}
            <div 
              class="slot"
              class:dragging={draggingSlot?.id === slot.id}
              draggable={!isFixed}
              style="
                top: {getSlotTop(slot)}px;
                height: {getSlotHeight(slot)}px;
                background-color: {getSlotColor(slot)};
                cursor: {isFixed ? 'pointer' : 'grab'};
              "
              on:click={() => handleSlotClick(slot)}
              on:dragstart={(e) => handleDragStart(e, slot)}
              on:dragend={handleDragEnd}
              title={task?.title || 'Unknown task'}
            >
              <div class="slot-title">
                {#if isFixed}🔒 {/if}{task?.title || 'Unknown'}
              </div>
              <div class="slot-time">
                {formatTime(slot.start_datetime)} - {formatTime(slot.end_datetime)}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .calendar-grid {
    display: grid;
    grid-template-columns: 60px repeat(7, 1fr);
    gap: 1px;
    background: #e5e7eb;
    border: 1px solid #e5e7eb;
  }

  .time-column {
    background: white;
  }

  .time-header {
    height: 50px;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
  }

  .time-label {
    height: 60px;
    padding: 4px 8px;
    font-size: 12px;
    color: #6b7280;
    text-align: right;
  }

  .day-column {
    background: white;
  }

  .day-header {
    height: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 14px;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
  }

  .day-header.today {
    background: #dbeafe;
    color: #1e40af;
  }

  .day-slots {
    position: relative;
    min-height: 540px;
  }

  .hour-block {
    height: 60px;
    border-bottom: 1px solid #f3f4f6;
  }

  .slot {
    position: absolute;
    left: 2px;
    right: 2px;
    border-radius: 4px;
    padding: 6px 8px;
    cursor: pointer;
    overflow: hidden;
    color: white;
    font-size: 12px;
    transition: all 0.2s;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  }

  .slot.dragging {
    opacity: 0.5;
    cursor: grabbing;
  }

  .slot[draggable="true"] {
    cursor: grab;
  }

  .slot[draggable="true"]:active {
    cursor: grabbing;
  }

  .slot:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    z-index: 10;
  }

  .slot-title {
    font-weight: 600;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .slot-time {
    font-size: 11px;
    opacity: 0.9;
  }
</style>
