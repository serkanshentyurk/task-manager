<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { api } from '../api.js';

  export let task = null;
  export let projects = [];

  const dispatch = createEventDispatcher();

  let formData = {
    title: task?.title || '',
    description: task?.description || '',
    priority: task?.priority || 3,
    estimated_hours: task?.estimated_hours || 4,
    min_session_hours: task?.min_session_hours || 2,
    start_date: task?.start_date || new Date().toISOString().split('T')[0],
    deadline: task?.deadline || '',
    project_id: task?.project_id || null,
    is_reschedulable: task?.is_reschedulable ?? true,
    has_recurrence: task?.has_recurrence || false,
    recurrence_frequency: task?.recurrence_frequency || 'weekly',
    recurrence_interval: task?.recurrence_interval || 1,
    recurrence_end_date: task?.recurrence_end_date || '',
    recurrence_days: task?.recurrence_days || 'MO,WE,FR',
  };

  let autoSchedule = !task; // Auto-schedule new tasks by default
  let forceBump = false;
  let saving = false;

  // Manual slots
  let showManualSlots = false;
  let manualSlots = [];
  let existingSlots = []; // For editing existing tasks
  let loadingSlots = false;
  let manualSlotForm = {
    date: new Date().toISOString().split('T')[0],
    start_time: '09:00',
    end_time: '11:00',
    is_fixed: false
  };

  // Load existing slots if editing a task
  onMount(async () => {
    if (task) {
      await loadExistingSlots();
    }
  });

  async function loadExistingSlots() {
    loadingSlots = true;
    try {
      // Get all slots for this task
      const today = new Date();
      const futureDate = new Date();
      futureDate.setFullYear(futureDate.getFullYear() + 1);
      
      const result = await api.getSlots(
        today.toISOString().split('T')[0],
        futureDate.toISOString().split('T')[0]
      );
      
      existingSlots = result.slots.filter(s => s.task_id === task.id && s.completed === 0);
    } catch (error) {
      console.error('Failed to load slots:', error);
    } finally {
      loadingSlots = false;
    }
  }

  function addManualSlot() {
    const startDateTime = new Date(`${manualSlotForm.date}T${manualSlotForm.start_time}`);
    const endDateTime = new Date(`${manualSlotForm.date}T${manualSlotForm.end_time}`);
    
    if (endDateTime <= startDateTime) {
      alert('End time must be after start time');
      return;
    }
    
    const duration = (endDateTime - startDateTime) / (1000 * 60 * 60);
    
    manualSlots = [...manualSlots, {
      start_datetime: startDateTime.toISOString(),
      end_datetime: endDateTime.toISOString(),
      is_fixed: manualSlotForm.is_fixed,
      duration_hours: duration
    }];
    
    // Reset form
    manualSlotForm = {
      date: new Date().toISOString().split('T')[0],
      start_time: '09:00',
      end_time: '11:00',
      is_fixed: false
    };
  }

  function removeManualSlot(index) {
    manualSlots = manualSlots.filter((_, i) => i !== index);
  }

  async function toggleSlotFixed(slot) {
    try {
      // We need an endpoint to update slot properties
      // For now, we'll just update locally and it will be handled on save
      const slotIndex = existingSlots.findIndex(s => s.id === slot.id);
      if (slotIndex !== -1) {
        existingSlots[slotIndex].is_fixed = existingSlots[slotIndex].is_fixed ? 0 : 1;
        existingSlots = [...existingSlots]; // Trigger reactivity
        
        // Update in backend
        await fetch(`http://localhost:8000/slots/${slot.id}/update-fixed`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_fixed: existingSlots[slotIndex].is_fixed })
        });
      }
    } catch (error) {
      console.error('Failed to toggle fixed status:', error);
      alert('Failed to update slot');
    }
  }

  async function deleteExistingSlot(slotId) {
    if (!confirm('Delete this time slot?')) return;
    
    try {
      await api.deleteSlot(slotId);
      existingSlots = existingSlots.filter(s => s.id !== slotId);
    } catch (error) {
      console.error('Failed to delete slot:', error);
      alert('Failed to delete slot');
    }
  }

  async function handleSubmit() {
    if (!formData.title) {
      alert('Please enter a task title');
      return;
    }

    if (!formData.start_date) {
      alert('Please enter a start date');
      return;
    }

    saving = true;
    try {
      let taskId = task?.id;
      
      if (task) {
        // Update existing task
        await api.updateTask(task.id, formData);
      } else {
        // Create new task
        let result;
        if (autoSchedule && manualSlots.length === 0) {
          result = await api.createTaskWithScheduling(formData, forceBump);
        } else {
          result = await api.createTask(formData);
        }
        taskId = result.id;
        
        // Create manual slots if any
        if (manualSlots.length > 0 && taskId) {
          for (const slot of manualSlots) {
            try {
              await api.createManualSlot({
                task_id: taskId,
                start_datetime: slot.start_datetime,
                end_datetime: slot.end_datetime,
                is_fixed: slot.is_fixed
              });
            } catch (error) {
              console.error('Failed to create manual slot:', error);
              alert(`Warning: Could not create slot at ${new Date(slot.start_datetime).toLocaleString()}`);
            }
          }
        }
      }
      
      // Create time allocation if recurring
      if (formData.has_recurrence && taskId) {
        // Convert simple fields to rrule format
        let rrule = `FREQ=${formData.recurrence_frequency.toUpperCase()}`;
        
        if (formData.recurrence_interval > 1) {
          rrule += `;INTERVAL=${formData.recurrence_interval}`;
        }
        
        if (formData.recurrence_frequency === 'weekly' && formData.recurrence_days) {
          rrule += `;BYDAY=${formData.recurrence_days}`;
        }
        
        if (formData.recurrence_end_date) {
          // Convert date to RRULE format: YYYYMMDD
          const endDate = new Date(formData.recurrence_end_date);
          const rruleDate = endDate.toISOString().split('T')[0].replace(/-/g, '');
          rrule += `;UNTIL=${rruleDate}`;
        }
        
        try {
          await api.createTimeAllocation({
            task_id: taskId,
            rrule: rrule,
            duration_hours: formData.min_session_hours,
            time_of_day: '09:00', // Default time, could be made configurable
            start_date: formData.start_date,
            end_date: formData.recurrence_end_date || null
          });
        } catch (error) {
          console.error('Failed to create recurrence:', error);
          alert('Warning: Task created but recurrence setup failed. ' + error.message);
        }
      }
      
      dispatch('saved');
    } catch (error) {
      alert('Failed to save task: ' + error.message);
    } finally {
      saving = false;
    }
  }

  function handleCancel() {
    dispatch('close');
  }
</script>

<div class="modal-overlay" on:click={handleCancel}>
  <div class="modal-content" on:click|stopPropagation>
    <div class="modal-header">
      {task ? 'Edit Task' : 'New Task'}
    </div>

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label class="form-label" for="title">Task Title *</label>
        <input 
          id="title"
          type="text" 
          class="form-input"
          bind:value={formData.title}
          placeholder="e.g., Write methods section"
          required
        />
      </div>

      <div class="form-group">
        <label class="form-label" for="description">Description</label>
        <textarea 
          id="description"
          class="form-textarea"
          bind:value={formData.description}
          placeholder="Additional details..."
        ></textarea>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
        <div class="form-group">
          <label class="form-label" for="priority">Priority</label>
          <select id="priority" class="form-select" bind:value={formData.priority}>
            <option value={1}>1 - Low</option>
            <option value={2}>2 - Medium-Low</option>
            <option value={3}>3 - Medium</option>
            <option value={4}>4 - High</option>
            <option value={5}>5 - Critical</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label" for="project">Project</label>
          <select id="project" class="form-select" bind:value={formData.project_id}>
            <option value={null}>No Project</option>
            {#each projects as project}
              <option value={project.id}>{project.name}</option>
            {/each}
          </select>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
        <div class="form-group">
          <label class="form-label" for="estimated_hours">Estimated Hours</label>
          <input 
            id="estimated_hours"
            type="number" 
            class="form-input"
            bind:value={formData.estimated_hours}
            min="0.5"
            step="0.5"
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="min_session">Min Session (hours)</label>
          <input 
            id="min_session"
            type="number" 
            class="form-input"
            bind:value={formData.min_session_hours}
            min="1"
            max="4"
            step="0.5"
          />
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
        <div class="form-group">
          <label class="form-label" for="start_date">Start Date *</label>
          <input 
            id="start_date"
            type="date" 
            class="form-input"
            bind:value={formData.start_date}
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="deadline">Deadline</label>
          <input 
            id="deadline"
            type="date" 
            class="form-input"
            bind:value={formData.deadline}
          />
        </div>
      </div>

      <div class="form-group">
        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
          <input 
            type="checkbox" 
            bind:checked={formData.is_reschedulable}
          />
          <span class="form-label" style="margin: 0;">Allow automatic rescheduling</span>
        </label>
      </div>

      <div class="form-group">
        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
          <input 
            type="checkbox" 
            bind:checked={formData.has_recurrence}
          />
          <span class="form-label" style="margin: 0;">🔁 Make this a recurring task</span>
        </label>
      </div>

      {#if formData.has_recurrence}
        <div style="padding: 16px; background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe; margin-bottom: 16px;">
          <div style="font-weight: 500; margin-bottom: 12px; color: #1e40af;">
            Recurrence Settings
          </div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
            <div>
              <label class="form-label">Frequency</label>
              <select class="form-input" bind:value={formData.recurrence_frequency}>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
            
            <div>
              <label class="form-label">
                Every {formData.recurrence_frequency === 'daily' ? 'days' : formData.recurrence_frequency === 'weekly' ? 'weeks' : 'months'}
              </label>
              <input 
                type="number" 
                min="1" 
                max="12"
                class="form-input"
                bind:value={formData.recurrence_interval}
              />
            </div>
          </div>
          
          {#if formData.recurrence_frequency === 'weekly'}
            <div style="margin-bottom: 12px;">
              <label class="form-label" style="display: block; margin-bottom: 8px;">
                On which days?
              </label>
              <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                {#each [
                  {value: 'MO', label: 'Mon'},
                  {value: 'TU', label: 'Tue'},
                  {value: 'WE', label: 'Wed'},
                  {value: 'TH', label: 'Thu'},
                  {value: 'FR', label: 'Fri'},
                  {value: 'SA', label: 'Sat'},
                  {value: 'SU', label: 'Sun'}
                ] as day}
                  <label style="
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    padding: 6px 12px;
                    border-radius: 6px;
                    border: 2px solid {formData.recurrence_days.includes(day.value) ? '#3b82f6' : '#e5e7eb'};
                    background: {formData.recurrence_days.includes(day.value) ? '#eff6ff' : 'white'};
                    cursor: pointer;
                    font-size: 13px;
                    font-weight: {formData.recurrence_days.includes(day.value) ? '600' : '400'};
                    color: {formData.recurrence_days.includes(day.value) ? '#1e40af' : '#6b7280'};
                  ">
                    <input 
                      type="checkbox" 
                      checked={formData.recurrence_days.includes(day.value)}
                      on:change={(e) => {
                        const days = formData.recurrence_days.split(',').filter(d => d);
                        if (e.target.checked) {
                          if (!days.includes(day.value)) {
                            days.push(day.value);
                          }
                        } else {
                          const index = days.indexOf(day.value);
                          if (index > -1) {
                            days.splice(index, 1);
                          }
                        }
                        formData.recurrence_days = days.join(',');
                      }}
                      style="margin: 0;"
                    />
                    {day.label}
                  </label>
                {/each}
              </div>
            </div>
          {/if}
          
          <div>
            <label class="form-label">End Date (optional)</label>
            <input 
              type="date" 
              class="form-input"
              bind:value={formData.recurrence_end_date}
              placeholder="Leave empty for no end date"
            />
            <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">
              Leave empty for ongoing recurrence
            </div>
          </div>
          
          <div style="margin-top: 12px; padding: 10px; background: white; border-radius: 6px; font-size: 13px; color: #6b7280;">
            <strong>Example:</strong>
            {#if formData.recurrence_frequency === 'daily'}
              Every {formData.recurrence_interval} day{formData.recurrence_interval > 1 ? 's' : ''}
            {:else if formData.recurrence_frequency === 'weekly'}
              Every {formData.recurrence_interval} week{formData.recurrence_interval > 1 ? 's' : ''} on {formData.recurrence_days.split(',').join(', ')}
            {:else}
              Every {formData.recurrence_interval} month{formData.recurrence_interval > 1 ? 's' : ''}
            {/if}
            {#if formData.recurrence_end_date}
              until {new Date(formData.recurrence_end_date).toLocaleDateString('en-GB')}
            {:else}
              (ongoing)
            {/if}
          </div>
        </div>
      {/if}

      {#if task && existingSlots.length > 0}
        <div style="padding: 12px; background: #fef3c7; border-radius: 6px; margin-bottom: 16px; border: 1px solid #fbbf24;">
          <div style="font-weight: 500; margin-bottom: 12px;">
            📅 Scheduled Time Slots ({existingSlots.length})
          </div>
          
          <div style="font-size: 13px; color: #92400e; margin-bottom: 12px;">
            You can delete slots or toggle them as fixed (🔒 prevents rescheduling)
          </div>
          
          {#each existingSlots as slot}
            <div style="padding: 10px; background: white; border-radius: 4px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 13px;">
              <div>
                <span style="font-weight: 500;">
                  {new Date(slot.start_datetime).toLocaleDateString('en-GB', { 
                    weekday: 'short', 
                    day: 'numeric', 
                    month: 'short' 
                  })}
                </span>
                <span style="color: #6b7280; margin: 0 6px;">•</span>
                <span>
                  {new Date(slot.start_datetime).toLocaleTimeString('en-GB', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                  -
                  {new Date(slot.end_datetime).toLocaleTimeString('en-GB', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
                <span style="color: #6b7280; margin: 0 6px;">•</span>
                <span style="color: #6b7280;">
                  {((new Date(slot.end_datetime) - new Date(slot.start_datetime)) / (1000 * 60 * 60)).toFixed(1)}h
                </span>
                {#if slot.is_fixed}
                  <span style="margin-left: 6px;">🔒 Fixed</span>
                {/if}
              </div>
              <div style="display: flex; gap: 6px;">
                <button 
                  type="button"
                  class="btn btn-sm {slot.is_fixed ? 'btn-secondary' : 'btn-primary'}"
                  on:click={() => toggleSlotFixed(slot)}
                  style="padding: 2px 8px; font-size: 12px;"
                  title={slot.is_fixed ? 'Unfix slot' : 'Fix slot'}
                >
                  {slot.is_fixed ? '🔓 Unfix' : '🔒 Fix'}
                </button>
                <button 
                  type="button"
                  class="btn btn-sm btn-danger"
                  on:click={() => deleteExistingSlot(slot.id)}
                  style="padding: 2px 8px; font-size: 12px;"
                >
                  Delete
                </button>
              </div>
            </div>
          {/each}
        </div>
      {/if}

      {#if !task}
        <div style="padding: 12px; background: #f3f4f6; border-radius: 6px; margin-bottom: 16px;">
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin-bottom: 8px;">
            <input 
              type="checkbox" 
              bind:checked={autoSchedule}
            />
            <span style="font-weight: 500;">Auto-schedule this task</span>
          </label>

          {#if autoSchedule}
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin-left: 28px;">
              <input 
                type="checkbox" 
                bind:checked={forceBump}
              />
              <span class="text-sm">Force bump lower priority tasks if needed</span>
            </label>
          {/if}
        </div>
      {/if}

      {#if !task}
        <div style="padding: 12px; background: #f0fdf4; border-radius: 6px; margin-bottom: 16px; border: 1px solid #86efac;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-weight: 500;">📅 Manual Time Slots</span>
            <button 
              type="button"
              class="btn btn-sm {showManualSlots ? 'btn-secondary' : 'btn-primary'}"
              on:click={() => showManualSlots = !showManualSlots}
            >
              {showManualSlots ? 'Hide' : 'Add Manual Slots'}
            </button>
          </div>
          
          {#if showManualSlots}
            <div style="padding: 12px; background: white; border-radius: 4px; margin-top: 12px;">
              <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px;">
                <div class="form-group" style="margin-bottom: 0;">
                  <label class="form-label text-xs">Date</label>
                  <input 
                    type="date" 
                    class="form-input"
                    bind:value={manualSlotForm.date}
                    style="padding: 6px 8px; font-size: 13px;"
                  />
                </div>
                
                <div class="form-group" style="margin-bottom: 0;">
                  <label class="form-label text-xs">Start Time</label>
                  <input 
                    type="time" 
                    class="form-input"
                    bind:value={manualSlotForm.start_time}
                    style="padding: 6px 8px; font-size: 13px;"
                  />
                </div>
                
                <div class="form-group" style="margin-bottom: 0;">
                  <label class="form-label text-xs">End Time</label>
                  <input 
                    type="time" 
                    class="form-input"
                    bind:value={manualSlotForm.end_time}
                    style="padding: 6px 8px; font-size: 13px;"
                  />
                </div>
              </div>
              
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 13px;">
                  <input 
                    type="checkbox" 
                    bind:checked={manualSlotForm.is_fixed}
                  />
                  <span>🔒 Fixed (cannot be rescheduled)</span>
                </label>
                
                <button 
                  type="button"
                  class="btn btn-sm btn-success"
                  on:click={addManualSlot}
                >
                  + Add Slot
                </button>
              </div>
            </div>
            
            {#if manualSlots.length > 0}
              <div style="margin-top: 12px;">
                <div style="font-size: 13px; font-weight: 500; margin-bottom: 6px; color: #374151;">
                  Added Slots ({manualSlots.length}):
                </div>
                {#each manualSlots as slot, index}
                  <div style="padding: 8px; background: white; border-radius: 4px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; font-size: 13px;">
                    <div>
                      <span style="font-weight: 500;">
                        {new Date(slot.start_datetime).toLocaleDateString('en-GB', { 
                          weekday: 'short', 
                          day: 'numeric', 
                          month: 'short' 
                        })}
                      </span>
                      <span style="color: #6b7280; margin: 0 6px;">•</span>
                      <span>
                        {new Date(slot.start_datetime).toLocaleTimeString('en-GB', { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                        -
                        {new Date(slot.end_datetime).toLocaleTimeString('en-GB', { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </span>
                      <span style="color: #6b7280; margin: 0 6px;">•</span>
                      <span style="color: #6b7280;">{slot.duration_hours}h</span>
                      {#if slot.is_fixed}
                        <span style="margin-left: 6px;">🔒</span>
                      {/if}
                    </div>
                    <button 
                      type="button"
                      class="btn btn-sm btn-danger"
                      on:click={() => removeManualSlot(index)}
                      style="padding: 2px 8px; font-size: 12px;"
                    >
                      Remove
                    </button>
                  </div>
                {/each}
              </div>
            {/if}
          {/if}
        </div>
      {/if}

      <div class="modal-footer">
        <button 
          type="button" 
          class="btn btn-secondary"
          on:click={handleCancel}
          disabled={saving}
        >
          Cancel
        </button>
        <button 
          type="submit" 
          class="btn btn-primary"
          disabled={saving}
        >
          {saving ? 'Saving...' : task ? 'Update' : 'Create'}
        </button>
      </div>
    </form>
  </div>
</div>
