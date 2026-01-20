<script>
  import { createEventDispatcher } from 'svelte';

  export let slot;
  export let task;

  const dispatch = createEventDispatcher();

  function handleComplete() {
    dispatch('complete', slot);
  }

  function handleEdit() {
    dispatch('edit', task);
  }

  function handleReschedule() {
    dispatch('reschedule', slot);
  }

  function handleCancel() {
    dispatch('cancel');
  }
</script>

<div class="modal-overlay" on:click={handleCancel}>
  <div class="modal-content slot-modal" on:click|stopPropagation>
    <div class="modal-header">
      {task?.title || 'Task'}
    </div>

    <div style="margin-bottom: 20px;">
      <div style="font-size: 14px; color: #6b7280; margin-bottom: 8px;">
        {new Date(slot.start_datetime).toLocaleString('en-GB', { 
          weekday: 'short', 
          day: 'numeric', 
          month: 'short',
          hour: '2-digit',
          minute: '2-digit'
        })}
        - 
        {new Date(slot.end_datetime).toLocaleTimeString('en-GB', { 
          hour: '2-digit', 
          minute: '2-digit' 
        })}
      </div>
      
      {#if task}
        <div style="font-size: 14px; color: #6b7280;">
          <span class="badge priority-{task.priority}">P{task.priority}</span>
          {#if task.project_name}
            <span style="margin-left: 8px;">{task.project_name}</span>
          {/if}
        </div>
      {/if}
    </div>

    <div class="modal-footer" style="display: flex; flex-direction: column; gap: 12px;">
      <button 
        class="btn btn-success"
        style="width: 100%;"
        on:click={handleComplete}
      >
        ✓ Mark Complete
      </button>
      
      <button 
        class="btn btn-warning"
        style="width: 100%;"
        on:click={handleReschedule}
      >
        🕐 Reschedule
      </button>
      
      <button 
        class="btn btn-primary"
        style="width: 100%;"
        on:click={handleEdit}
      >
        ✏️ Edit Task
      </button>
      
      <button 
        class="btn btn-secondary"
        style="width: 100%;"
        on:click={handleCancel}
      >
        Cancel
      </button>
    </div>
  </div>
</div>

<style>
  .slot-modal {
    max-width: 400px;
  }
</style>
