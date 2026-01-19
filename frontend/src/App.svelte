<script>
  import { onMount } from 'svelte';
  import Calendar from './components/Calendar.svelte';
  import TaskList from './components/TaskList.svelte';
  import TaskForm from './components/TaskForm.svelte';
  import Dashboard from './components/Dashboard.svelte';
  import { api } from './api.js';

  let showTaskForm = false;
  let editingTask = null;
  let tasks = [];
  let projects = [];
  let slots = [];
  let stats = {};
  let loading = true;

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
      
      tasks = tasksRes.tasks || [];
      projects = projectsRes.projects || [];
      slots = slotsRes.slots || [];
      stats = statsRes;
    } catch (error) {
      console.error('Failed to load data:', error);
      alert('Failed to load data. Make sure the backend is running.');
    } finally {
      loading = false;
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
    
    const action = confirm(`Task: ${task.title}\n\nClick OK to mark slot complete, Cancel to edit task`);
    if (action) {
      try {
        await api.completeSlot(slot.id);
        await loadData();
      } catch (error) {
        alert('Failed to complete slot: ' + error.message);
      }
    } else {
      openTaskForm(task);
    }
  }
</script>

<svelte:head>
  <title>PhD Task Manager</title>
</svelte:head>

<main class="container">
  <header style="margin-bottom: 24px;">
    <div class="flex items-center justify-between">
      <h1 style="font-size: 28px; font-weight: 700;">PhD Task Manager</h1>
      <div class="flex gap-2">
        <button class="btn btn-success" on:click={handleAutoSchedule}>
          ⚡ Auto-Schedule
        </button>
        <button class="btn btn-primary" on:click={() => openTaskForm()}>
          + New Task
        </button>
      </div>
    </div>
  </header>

  {#if loading}
    <div style="display: flex; justify-content: center; padding: 40px;">
      <div class="spinner"></div>
    </div>
  {:else}
    <div style="margin-bottom: 20px;">
      <Dashboard {stats} />
    </div>

    <div class="grid grid-cols-4">
      <div class="col-span-3">
        <Calendar 
          {slots} 
          {tasks}
          {startDate}
          {endDate}
          on:slotClick={(e) => handleSlotClick(e.detail)}
          on:dateChange={(e) => {
            startDate = e.detail.start;
            endDate = e.detail.end;
            loadData();
          }}
        />
      </div>

      <div>
        <TaskList 
          {tasks}
          {projects}
          on:taskClick={(e) => openTaskForm(e.detail)}
          on:taskComplete={(e) => handleTaskComplete(e.detail)}
          on:taskDelete={(e) => handleTaskDelete(e.detail)}
        />
      </div>
    </div>
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

<style>
  main {
    padding-top: 20px;
    padding-bottom: 40px;
  }
</style>
