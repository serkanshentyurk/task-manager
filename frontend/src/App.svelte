<script>
  import { onMount } from 'svelte';
  import Calendar from './components/Calendar.svelte';
  import TaskList from './components/TaskList.svelte';
  import TaskForm from './components/TaskForm.svelte';
  import Dashboard from './components/Dashboard.svelte';
  import SlotActionModal from './components/SlotActionModal.svelte';
  import ConflictResolutionModal from './components/ConflictResolutionModal.svelte';
  import RescheduleSlotModal from './components/RescheduleSlotModal.svelte';
  import FillSlotModal from './components/FillSlotModal.svelte';
  import SettingsModal from './components/SettingsModal.svelte';
  import MonthView from './components/MonthView.svelte';
  import ProjectsView from './components/ProjectsView.svelte';
  import { api } from './api.js';

  let currentView = 'dashboard'; // 'dashboard' or 'projects'
  let calendarView = 'week'; // 'week' or 'month'
  let showTaskForm = false;
  let showSlotModal = false;
  let showConflictModal = false;
  let showRescheduleModal = false;
  let showFillSlotModal = false;
  let showSettings = false;
  let editingTask = null;
  let selectedSlot = null;
  let pendingMove = null; // {slot, newStart, conflictingSlot}
  let fillSlotData = null; // {startTime, endTime, suggestions, availableDuration}
  let tasks = [];
  let projects = [];
  let slots = [];
  let stats = {};
  let loading = true;
  let sanityCheckResults = null;

  // Helper to get week start (Monday)
  function getWeekStart(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff));
  }

  // Date range for calendar (current week)
  let currentDate = new Date();
  let startDate = getWeekStart(currentDate);
  let endDate = new Date(startDate);
  endDate.setDate(startDate.getDate() + 6); // End of week (Sunday)

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    loading = true;
    try {
      const [tasksRes, projectsRes, slotsRes, statsRes] = await Promise.all([
        api.getTasks(),
        api.getProjects(),
        api.getSlots(
          startDate.toISOString().split('T')[0],
          endDate.toISOString().split('T')[0]
        ),
        api.getStats(),
      ]);
      
      // Force new array references to trigger Svelte reactivity
      tasks = [...(tasksRes.tasks || [])];
      projects = [...(projectsRes.projects || [])];
      slots = [...(slotsRes.slots || [])];
      stats = {...statsRes};
      
      // Run sanity check
      await runSanityCheck();
    } catch (error) {
      console.error('Failed to load data:', error);
      alert('Failed to load data. Make sure the backend is running.');
    } finally {
      loading = false;
    }
  }

  async function runSanityCheck() {
    try {
      sanityCheckResults = await api.sanityCheckTasks();
      if (sanityCheckResults.mismatch_count > 0) {
        console.warn(`⚠️ Sanity check found ${sanityCheckResults.mismatch_count} tasks with scheduling mismatches`);
      }
    } catch (error) {
      console.error('Failed to run sanity check:', error);
    }
  }

  async function handleFixMismatch(event) {
    const { task, mismatch, action } = event.detail;
    
    if (action === 'reschedule') {
      // Delete all non-fixed slots and auto-reschedule
      if (!confirm(`Delete all slots for "${task.title}" and auto-reschedule to match ${task.estimated_hours}h?`)) return;
      
      try {
        // Delete all incomplete, non-fixed slots
        const taskSlots = slots.filter(s => s.task_id === task.id && !s.completed && !s.is_fixed);
        for (const slot of taskSlots) {
          await api.deleteSlot(slot.id);
        }
        
        // Auto-schedule the task
        await api.scheduleTask(task.id, false);
        await loadData();
        alert('✓ Task rescheduled successfully!');
      } catch (error) {
        alert('Failed to reschedule: ' + error.message);
      }
    } else if (action === 'update_estimated') {
      // Update estimated_hours to match scheduled hours
      if (!confirm(`Update "${task.title}" estimated hours from ${task.estimated_hours}h to ${mismatch.scheduled_hours}h?`)) return;
      
      try {
        await api.updateTask(task.id, { estimated_hours: mismatch.scheduled_hours });
        await loadData();
        alert('✓ Estimated hours updated!');
      } catch (error) {
        alert('Failed to update: ' + error.message);
      }
    } else if (action === 'edit') {
      // Just open the task form
      openTaskForm(task);
    }
  }

  async function handleAutoSchedule() {
    if (!confirm('Auto-schedule all unscheduled tasks?')) return;
    
    try {
      const result = await api.autoSchedule();
      alert(`Scheduled: ${result.scheduled.length}, Partial: ${result.partial.length}, Failed: ${result.failed.length}`);
      await loadData();
    } catch (error) {
      alert('Auto-schedule failed: ' + error.message);
    }
  }

  function openTaskForm(task = null) {
    editingTask = task;
    showTaskForm = true;
  }

  function closeTaskForm() {
    showTaskForm = false;
    editingTask = null;
  }

  async function handleTaskSaved() {
    closeTaskForm();
    await loadData();
  }

  async function handleTaskComplete(taskId) {
    if (!confirm('Mark this task as complete? Future slots will be deleted.')) return;
    
    try {
      await api.completeTask(taskId);
      await loadData();
    } catch (error) {
      alert('Failed to complete task: ' + error.message);
    }
  }

  async function handleTaskDelete(taskId) {
    if (!confirm('Delete this task and all its scheduled slots?')) return;
    
    try {
      await api.deleteTask(taskId);
      await loadData();
    } catch (error) {
      alert('Failed to delete task: ' + error.message);
    }
  }

  async function handleSlotClick(slot) {
    const task = tasks.find(t => t.id === slot.task_id);
    if (!task) return;
    
    // Open modal instead of confirm dialog
    selectedSlot = slot;
    editingTask = task;
    showSlotModal = true;
  }

  async function handleSlotComplete(event) {
    const slot = event.detail;
    const task = tasks.find(t => t.id === slot.task_id);
    
    try {
      console.log('Completing slot:', slot.id);
      const result = await api.completeSlot(slot.id);
      console.log('Slot completed, reloading data...');
      await loadData();
      console.log('Data reloaded. Slots count:', slots.length);
      
      // Show message if task was auto-completed
      if (result.task_completed) {
        alert(`✓ Slot completed!\n\nAll slots for "${task.title}" are now done.\nTask marked as complete! 🎉`);
      }
    } catch (error) {
      console.error('Failed to complete slot:', error);
      alert('Failed to complete slot: ' + error.message);
    } finally {
      showSlotModal = false;
      selectedSlot = null;
      editingTask = null;
    }
  }

  function handleSlotEdit(event) {
    const task = event.detail;
    showSlotModal = false;
    selectedSlot = null;
    openTaskForm(task);
  }

  function handleSlotReschedule(event) {
    const slot = event.detail;
    showSlotModal = false;
    showRescheduleModal = true;
    // selectedSlot and editingTask are already set
  }

  async function handleRescheduleSave(event) {
    const { newStart } = event.detail;
    
    if (!selectedSlot) return;
    
    try {
      const result = await api.moveSlot(selectedSlot.id, newStart);
      
      if (result.conflict) {
        // Show conflict resolution modal
        pendingMove = {
          slot: selectedSlot,
          newStart,
          conflictingSlot: result.conflicting_slot
        };
        showRescheduleModal = false;
        showConflictModal = true;
      } else {
        // Move successful
        await loadData();
        showRescheduleModal = false;
        selectedSlot = null;
        editingTask = null;
      }
    } catch (error) {
      console.error('Failed to reschedule slot:', error);
      alert('Failed to reschedule slot: ' + error.message);
    }
  }

  async function handleCreateProject(event) {
    try {
      await api.createProject(event.detail);
      await loadData();
      alert('✓ Project created!');
    } catch (error) {
      alert('Failed to create project: ' + error.message);
    }
  }

  async function handleDeleteProject(event) {
    try {
      await api.deleteProject(event.detail);
      await loadData();
      alert('✓ Project deleted!');
    } catch (error) {
      alert('Failed to delete project: ' + error.message);
    }
  }

  async function handleEmptySlotClick(event) {
    const { startTime, endTime } = event.detail;
    
    console.log('Empty slot clicked in app:', { startTime, endTime });
    
    try {
      const result = await api.getFillSuggestions(startTime, endTime);
      
      fillSlotData = {
        startTime,
        endTime,
        suggestions: result.suggestions,
        availableDuration: result.available_duration
      };
      
      showFillSlotModal = true;
    } catch (error) {
      console.error('Failed to get fill suggestions:', error);
      alert('Failed to get suggestions: ' + error.message);
    }
  }

  async function handleFillSlotSelect(event) {
    const suggestion = event.detail;
    
    if (!fillSlotData) return;
    
    try {
      // Move the slot to the empty time
      await api.moveSlot(suggestion.slot_id, fillSlotData.startTime);
      await loadData();
      showFillSlotModal = false;
      fillSlotData = null;
      alert(`✓ "${suggestion.task_title}" moved to fill this slot!`);
    } catch (error) {
      console.error('Failed to move slot:', error);
      alert('Failed to move slot: ' + error.message);
    }
  }

  function handleFillSlotCancel() {
    showFillSlotModal = false;
    fillSlotData = null;
  }

  function handleRescheduleCancel() {
    showRescheduleModal = false;
    selectedSlot = null;
    editingTask = null;
  }

  function handleSlotModalCancel() {
    showSlotModal = false;
    selectedSlot = null;
    editingTask = null;
  }

  async function handleSlotMove(event) {
    console.log('handleSlotMove called with event:', event.detail);
    const { slot, newStart } = event.detail;
    
    console.log('Moving slot:', { slotId: slot.id, newStart });
    
    try {
      const result = await api.moveSlot(slot.id, newStart);
      
      console.log('Move slot result:', result);
      
      if (result.conflict) {
        console.log('Conflict detected:', result.conflicting_slot);
        // Show conflict resolution modal
        pendingMove = {
          slot,
          newStart,
          conflictingSlot: result.conflicting_slot
        };
        showConflictModal = true;
      } else {
        console.log('Move successful, reloading data...');
        // Move successful
        await loadData();
        console.log('Data reloaded');
      }
    } catch (error) {
      console.error('Failed to move slot:', error);
      alert('Failed to move slot: ' + error.message);
    }
  }

  async function handleConflictSwap() {
    if (!pendingMove) return;
    
    try {
      await api.moveSlotWithSwap(
        pendingMove.slot.id,
        pendingMove.conflictingSlot.id,
        pendingMove.newStart
      );
      await loadData();
    } catch (error) {
      alert('Failed to swap slots: ' + error.message);
    } finally {
      showConflictModal = false;
      pendingMove = null;
    }
  }

  function handleConflictCancel() {
    showConflictModal = false;
    pendingMove = null;
  }
</script>

<svelte:head>
  <title>Task Manager</title>
</svelte:head>

<main class="container">
  <header style="margin-bottom: 24px;">
    <div class="flex items-center justify-between">
      <h1 style="font-size: 28px; font-weight: 700;">Task Manager</h1>
      <div class="flex gap-2">
        <button class="btn btn-secondary" on:click={() => showSettings = true} title="Settings">
          ⚙️
        </button>
        <button class="btn btn-success" on:click={handleAutoSchedule}>
          ⚡ Auto-Schedule
        </button>
        <button class="btn btn-primary" on:click={() => openTaskForm()}>
          + New Task
        </button>
      </div>
    </div>
    
    <!-- Navigation Tabs -->
    <div style="margin-top: 20px; border-bottom: 2px solid #e5e7eb;">
      <div style="display: flex; gap: 8px;">
        <button
          class="btn btn-sm"
          style="
            border-radius: 8px 8px 0 0;
            border-bottom: 3px solid {currentView === 'dashboard' ? '#3b82f6' : 'transparent'};
            background: {currentView === 'dashboard' ? '#eff6ff' : 'transparent'};
            color: {currentView === 'dashboard' ? '#3b82f6' : '#6b7280'};
            font-weight: {currentView === 'dashboard' ? '600' : '400'};
          "
          on:click={() => currentView = 'dashboard'}
        >
          📅 Dashboard
        </button>
        <button
          class="btn btn-sm"
          style="
            border-radius: 8px 8px 0 0;
            border-bottom: 3px solid {currentView === 'projects' ? '#3b82f6' : 'transparent'};
            background: {currentView === 'projects' ? '#eff6ff' : 'transparent'};
            color: {currentView === 'projects' ? '#3b82f6' : '#6b7280'};
            font-weight: {currentView === 'projects' ? '600' : '400'};
          "
          on:click={() => currentView = 'projects'}
        >
          📁 Projects
        </button>
      </div>
    </div>
  </header>

  {#if loading}
    <div style="display: flex; justify-content: center; padding: 40px;">
      <div class="spinner"></div>
    </div>
  {:else if currentView === 'dashboard'}
    <div style="margin-bottom: 20px;">
      <Dashboard {stats} />
    </div>

    <!-- Calendar View Toggle -->
    <div style="margin-bottom: 16px; display: flex; justify-content: flex-end;">
      <div style="display: flex; gap: 4px; background: #f3f4f6; padding: 4px; border-radius: 8px;">
        <button
          class="btn btn-sm"
          style="
            background: {calendarView === 'week' ? 'white' : 'transparent'};
            font-weight: {calendarView === 'week' ? '600' : '400'};
            box-shadow: {calendarView === 'week' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none'};
          "
          on:click={() => calendarView = 'week'}
        >
          📅 Week
        </button>
        <button
          class="btn btn-sm"
          style="
            background: {calendarView === 'month' ? 'white' : 'transparent'};
            font-weight: {calendarView === 'month' ? '600' : '400'};
            box-shadow: {calendarView === 'month' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none'};
          "
          on:click={() => calendarView = 'month'}
        >
          📆 Month
        </button>
      </div>
    </div>

    <div class="grid grid-cols-4">
      <div class="col-span-3">
        {#if calendarView === 'week'}
          <Calendar 
            slots={slots}
            {tasks}
            {startDate}
            {endDate}
            on:slotClick={(e) => handleSlotClick(e.detail)}
            on:slotMove={(e) => handleSlotMove(e)}
            on:emptySlotClick={handleEmptySlotClick}
            on:dateChange={(e) => {
              startDate = e.detail.start;
              endDate = e.detail.end;
              loadData();
            }}
          />
        {:else}
          <MonthView
            {slots}
            {tasks}
            {projects}
            on:slotClick={(e) => handleSlotClick(e.detail)}
            on:dateChange={async (e) => {
              const month = e.detail.month;
              startDate = new Date(month.getFullYear(), month.getMonth(), 1);
              endDate = new Date(month.getFullYear(), month.getMonth() + 1, 0);
              await loadData();
            }}
          />
        {/if}
      </div>

      <div>
        <TaskList 
          {tasks}
          {projects}
          {sanityCheckResults}
          on:taskClick={(e) => openTaskForm(e.detail)}
          on:taskComplete={(e) => handleTaskComplete(e.detail)}
          on:taskDelete={(e) => handleTaskDelete(e.detail)}
          on:fixMismatch={handleFixMismatch}
        />
      </div>
    </div>
  {:else if currentView === 'projects'}
    <ProjectsView
      {projects}
      {tasks}
      {slots}
      on:createProject={handleCreateProject}
      on:deleteProject={handleDeleteProject}
      on:taskClick={(e) => openTaskForm(e.detail)}
    />
  {/if}
</main>

{#if showTaskForm}
  <TaskForm 
    task={editingTask}
    {projects}
    on:close={closeTaskForm}
    on:saved={handleTaskSaved}
  />
{/if}

{#if showSlotModal && selectedSlot}
  <SlotActionModal 
    slot={selectedSlot}
    task={editingTask}
    on:complete={handleSlotComplete}
    on:edit={handleSlotEdit}
    on:reschedule={handleSlotReschedule}
    on:cancel={handleSlotModalCancel}
  />
{/if}

{#if showRescheduleModal && selectedSlot}
  <RescheduleSlotModal 
    slot={selectedSlot}
    task={editingTask}
    on:save={handleRescheduleSave}
    on:cancel={handleRescheduleCancel}
  />
{/if}

{#if showConflictModal && pendingMove}
  <ConflictResolutionModal 
    movingSlot={pendingMove.slot}
    conflictingSlot={pendingMove.conflictingSlot}
    newTime={pendingMove.newStart}
    on:swap={handleConflictSwap}
    on:cancel={handleConflictCancel}
  />
{/if}

{#if showFillSlotModal && fillSlotData}
  <FillSlotModal
    startTime={fillSlotData.startTime}
    endTime={fillSlotData.endTime}
    suggestions={fillSlotData.suggestions}
    availableDuration={fillSlotData.availableDuration}
    on:select={handleFillSlotSelect}
    on:cancel={handleFillSlotCancel}
  />
{/if}

{#if showSettings}
  <SettingsModal
    on:saved={() => {
      showSettings = false;
      loadData();
    }}
    on:close={() => showSettings = false}
  />
{/if}

<style>
  main {
    padding-top: 20px;
    padding-bottom: 40px;
  }
</style>
