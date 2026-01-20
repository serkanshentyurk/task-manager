<script>
  import { createEventDispatcher } from 'svelte';

  export let slot;
  export let task;

  const dispatch = createEventDispatcher();

  // Parse current time
  const currentStart = new Date(slot.start_datetime);
  const currentEnd = new Date(slot.end_datetime);
  const duration = (currentEnd - currentStart) / (1000 * 60 * 60); // hours

  let newDate = currentStart.toISOString().split('T')[0];
  let newStartTime = currentStart.toTimeString().substring(0, 5);
  let newEndTime = '';

  function handleSave() {
    // Create new datetime
    const newStart = new Date(`${newDate}T${newStartTime}`);
    dispatch('save', { newStart: newStart.toISOString() });
  }

  function handleCancel() {
    dispatch('cancel');
  }

  // Calculate new end time for display
  $: {
    const start = new Date(`${newDate}T${newStartTime}`);
    const end = new Date(start.getTime() + duration * 60 * 60 * 1000);
    newEndTime = end.toTimeString().substring(0, 5);
  }
</script>

<div class="modal-overlay" on:click={handleCancel}>
  <div class="modal-content" on:click|stopPropagation>
    <div class="modal-header">
      🕐 Reschedule Slot
    </div>

    <div style="margin-bottom: 20px;">
      <div style="font-weight: 500; margin-bottom: 8px;">
        {task?.title || 'Task'}
      </div>
      
      <div style="font-size: 13px; color: #6b7280; margin-bottom: 16px;">
        Duration: {duration}h
      </div>

      <div class="form-group">
        <label class="form-label">Date</label>
        <input 
          type="date" 
          class="form-input"
          bind:value={newDate}
        />
      </div>

      <div class="form-group">
        <label class="form-label">Start Time</label>
        <input 
          type="time" 
          class="form-input"
          bind:value={newStartTime}
        />
      </div>

      <div style="padding: 10px; background: #f3f4f6; border-radius: 4px; font-size: 13px;">
        <strong>New time:</strong> {newStartTime} - {newEndTime}
      </div>
    </div>

    <div class="modal-footer">
      <button 
        class="btn btn-secondary"
        on:click={handleCancel}
      >
        Cancel
      </button>
      <button 
        class="btn btn-primary"
        on:click={handleSave}
      >
        Save
      </button>
    </div>
  </div>
</div>

<style>
  .modal-content {
    max-width: 400px;
  }
</style>
