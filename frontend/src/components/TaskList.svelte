<script>
  import { createEventDispatcher } from 'svelte';

  export let tasks = [];
  export let projects = [];

  const dispatch = createEventDispatcher();

  let filter = 'active'; // 'all', 'active', 'completed', 'unscheduled'

  $: filteredTasks = tasks.filter(task => {
    if (filter === 'all') return true;
    if (filter === 'active') return task.status !== 'completed';
    if (filter === 'completed') return task.status === 'completed';
    if (filter === 'unscheduled') return task.status !== 'completed'; // Will check scheduled status
    return true;
  }).sort((a, b) => {
    // Sort by deadline, then priority
    if (a.deadline && b.deadline) {
      const dateCompare = new Date(a.deadline) - new Date(b.deadline);
      if (dateCompare !== 0) return dateCompare;
    }
    return b.priority - a.priority;
  });

  function getProjectName(projectId) {
    const project = projects.find(p => p.id === projectId);
    return project ? project.name : 'No Project';
  }

  function getProjectColor(projectId) {
    const project = projects.find(p => p.id === projectId);
    return project ? project.colour : '#6b7280';
  }

  function formatDate(dateStr) {
    if (!dateStr) return 'No deadline';
    const date = new Date(dateStr);
    const today = new Date();
    const diffDays = Math.ceil((date - today) / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return '⚠️ Overdue';
    if (diffDays === 0) return '🔥 Today';
    if (diffDays === 1) return '⚡ Tomorrow';
    if (diffDays <= 7) return `${diffDays} days`;
    return date.toLocaleDateString();
  }
</script>

<div class="card">
  <div class="card-header">
    <span>Tasks</span>
  </div>

  <div style="margin-bottom: 16px; display: flex; gap: 8px; flex-wrap: wrap;">
    <button 
      class="btn btn-sm {filter === 'active' ? 'btn-primary' : 'btn-secondary'}"
      on:click={() => filter = 'active'}
    >
      Active
    </button>
    <button 
      class="btn btn-sm {filter === 'all' ? 'btn-primary' : 'btn-secondary'}"
      on:click={() => filter = 'all'}
    >
      All
    </button>
    <button 
      class="btn btn-sm {filter === 'completed' ? 'btn-primary' : 'btn-secondary'}"
      on:click={() => filter = 'completed'}
    >
      Done
    </button>
  </div>

  <div style="max-height: 600px; overflow-y: auto;">
    {#if filteredTasks.length === 0}
      <div style="padding: 20px; text-align: center; color: #9ca3af;">
        No tasks found
      </div>
    {:else}
      {#each filteredTasks as task}
        <div 
          class="task-item"
          on:click={() => dispatch('taskClick', task)}
        >
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;">
            <div class="task-title" style="flex: 1;">
              {task.title}
            </div>
            <span class="badge priority-{task.priority}">
              P{task.priority}
            </span>
          </div>
          
          <div class="task-meta">
            <span>{formatDate(task.deadline)}</span>
            <span>•</span>
            <span>{task.estimated_hours}h</span>
            {#if task.project_id}
              <span>•</span>
              <span style="color: {getProjectColor(task.project_id)};">
                {getProjectName(task.project_id)}
              </span>
            {/if}
          </div>

          <div style="margin-top: 8px; display: flex; gap: 6px;">
            {#if task.status !== 'completed'}
              <button 
                class="btn btn-sm btn-success"
                on:click|stopPropagation={() => dispatch('taskComplete', task.id)}
              >
                ✓ Complete
              </button>
            {/if}
            <button 
              class="btn btn-sm btn-danger"
              on:click|stopPropagation={() => dispatch('taskDelete', task.id)}
            >
              Delete
            </button>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .task-item {
    transition: all 0.2s;
  }

  .task-item:hover {
    transform: translateY(-1px);
  }
</style>
