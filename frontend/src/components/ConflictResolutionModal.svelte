<script>
  import { createEventDispatcher } from 'svelte';

  export let movingSlot;
  export let conflictingSlot;
  export let newTime;

  const dispatch = createEventDispatcher();

  function handleSwap() {
    dispatch('swap');
  }

  function handleCancel() {
    dispatch('cancel');
  }
</script>

<div class="modal-overlay" on:click={handleCancel}>
  <div class="modal-content" on:click|stopPropagation>
    <div class="modal-header">
      ⚠️ Time Slot Conflict
    </div>

    <div style="margin-bottom: 20px;">
      <p style="margin-bottom: 12px; color: #6b7280;">
        The time slot you selected conflicts with another event:
      </p>
      
      <div style="padding: 12px; background: #fee2e2; border-radius: 6px; border-left: 3px solid #ef4444; margin-bottom: 16px;">
        <div style="font-weight: 600; margin-bottom: 4px;">
          {conflictingSlot.task_title}
        </div>
        <div style="font-size: 13px; color: #6b7280;">
          {new Date(conflictingSlot.start).toLocaleString('en-GB', { 
            weekday: 'short',
            hour: '2-digit',
            minute: '2-digit'
          })}
          -
          {new Date(conflictingSlot.end).toLocaleTimeString('en-GB', { 
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
        {#if conflictingSlot.is_fixed}
          <div style="margin-top: 6px; font-size: 13px; color: #dc2626;">
            🔒 This slot is fixed and cannot be moved
          </div>
        {/if}
      </div>

      <p style="font-size: 14px; font-weight: 500; margin-bottom: 8px;">
        What would you like to do?
      </p>
    </div>

    <div class="modal-footer" style="display: flex; flex-direction: column; gap: 10px;">
      {#if !conflictingSlot.is_fixed}
        <button 
          class="btn btn-primary"
          style="width: 100%;"
          on:click={handleSwap}
        >
          🔄 Swap Both Events
        </button>
      {/if}
      
      <button 
        class="btn btn-secondary"
        style="width: 100%;"
        on:click={handleCancel}
      >
        ✖️ Cancel Move
      </button>
    </div>
  </div>
</div>

<style>
  .modal-content {
    max-width: 450px;
  }
</style>
