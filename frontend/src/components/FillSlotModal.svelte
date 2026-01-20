<script>
  import { createEventDispatcher } from 'svelte';
  
  export let startTime;
  export let endTime;
  export let suggestions = [];
  export let availableDuration = 0;
  
  const dispatch = createEventDispatcher();
  
  function formatTime(datetime) {
    return new Date(datetime).toLocaleTimeString('en-GB', { 
      hour: '2-digit', 
      minute: '2-digit'
    });
  }
  
  function formatDate(datetime) {
    const date = new Date(datetime);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === tomorrow.toDateString()) {
      return 'Tomorrow';
    } else {
      return date.toLocaleDateString('en-GB', { 
        weekday: 'short',
        month: 'short', 
        day: 'numeric' 
      });
    }
  }
  
  function handleSelect(suggestion) {
    dispatch('select', suggestion);
  }
  
  function handleCancel() {
    dispatch('cancel');
  }
</script>

<div class="modal-overlay" on:click={handleCancel}>
  <div class="modal-content" on:click|stopPropagation style="max-width: 600px; max-height: 80vh;">
    <div class="modal-header">
      <h3>Fill This Time Slot</h3>
      <button class="btn-close" on:click={handleCancel}>✕</button>
    </div>
    
    <div class="modal-body" style="max-height: 60vh; overflow-y: auto;">
      <div style="background: #eff6ff; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
        <div style="font-size: 14px; color: #1e40af; margin-bottom: 4px;">
          <strong>Available Time:</strong>
        </div>
        <div style="font-size: 18px; font-weight: 600; color: #1e40af;">
          {formatTime(startTime)} - {formatTime(endTime)} ({availableDuration}h available)
        </div>
      </div>
      
      {#if suggestions.length === 0}
        <div style="
          padding: 40px;
          text-align: center;
          background: #f9fafb;
          border-radius: 8px;
          color: #6b7280;
        ">
          <div style="font-size: 48px; margin-bottom: 12px;">📭</div>
          <div style="font-size: 16px; font-weight: 500; margin-bottom: 8px;">
            No suitable tasks found
          </div>
          <div style="font-size: 13px;">
            All your future tasks are either too long, fixed, or non-reschedulable.
          </div>
        </div>
      {:else}
        <div style="margin-bottom: 12px; color: #6b7280; font-size: 13px;">
          Found {suggestions.length} tasks you could move here:
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 8px;">
          {#each suggestions as suggestion}
            <button
              class="suggestion-card"
              on:click={() => handleSelect(suggestion)}
            >
              <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                <div style="flex: 1;">
                  <div style="font-size: 15px; font-weight: 600; color: #1f2937; margin-bottom: 4px;">
                    {suggestion.task_title}
                  </div>
                  <div style="font-size: 13px; color: #6b7280;">
                    Currently: {formatDate(suggestion.current_start)} at {formatTime(suggestion.current_start)}
                  </div>
                </div>
                <span class="badge priority-{suggestion.priority}">
                  P{suggestion.priority}
                </span>
              </div>
              
              <div style="display: flex; gap: 16px; font-size: 12px; color: #6b7280;">
                <div>
                  <span style="font-weight: 500;">Duration:</span> {suggestion.duration}h
                </div>
                {#if suggestion.days_until === 0}
                  <div style="color: #10b981; font-weight: 500;">
                    ⏰ Later today
                  </div>
                {:else if suggestion.days_until === 1}
                  <div style="color: #3b82f6; font-weight: 500;">
                    📅 Tomorrow
                  </div>
                {:else}
                  <div>
                    📅 In {suggestion.days_until} days
                  </div>
                {/if}
              </div>
              
              {#if suggestion.deadline}
                <div style="
                  margin-top: 8px;
                  padding-top: 8px;
                  border-top: 1px solid #e5e7eb;
                  font-size: 12px;
                  color: #9ca3af;
                ">
                  Deadline: {new Date(suggestion.deadline).toLocaleDateString('en-GB', { 
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric'
                  })}
                </div>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    </div>
    
    <div class="modal-footer">
      <button class="btn btn-secondary" on:click={handleCancel}>
        Cancel
      </button>
    </div>
  </div>
</div>

<style>
  .suggestion-card {
    width: 100%;
    padding: 16px;
    text-align: left;
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .suggestion-card:hover {
    border-color: #3b82f6;
    background: #eff6ff;
    transform: translateY(-2px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }
</style>
