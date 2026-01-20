<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { api } from '../api.js';
  
  const dispatch = createEventDispatcher();
  
  let settings = {
    work_start_hour: 9,
    work_end_hour: 18,
    work_schedule: 'weekdays',
    custom_days: 'MO,TU,WE,TH,FR',
    lunch_break_enabled: true,
    lunch_break_start: '12:00',
    lunch_break_duration: 1.0
  };
  
  let blockedTimes = [];
  let loading = true;
  let saving = false;
  
  // New blocked time form
  let showAddBlock = false;
  let newBlock = {
    title: '',
    start_datetime: '',
    end_datetime: '',
    recurring: false
  };
  
  onMount(async () => {
    await loadSettings();
    await loadBlockedTimes();
    loading = false;
  });
  
  async function loadSettings() {
    try {
      const response = await api.getCalendarSettings();
      settings = { ...settings, ...response.settings };
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  }
  
  async function loadBlockedTimes() {
    try {
      const response = await api.getBlockedTimes();
      blockedTimes = response.blocked_times || [];
    } catch (error) {
      console.error('Failed to load blocked times:', error);
    }
  }
  
  async function handleSave() {
    saving = true;
    try {
      await api.updateCalendarSettings(settings);
      alert('✓ Settings saved!');
      dispatch('saved');
    } catch (error) {
      alert('Failed to save settings: ' + error.message);
    } finally {
      saving = false;
    }
  }
  
  async function handleAddBlockedTime() {
    if (!newBlock.title || !newBlock.start_datetime || !newBlock.end_datetime) {
      alert('Please fill in all fields');
      return;
    }
    
    try {
      await api.createBlockedTime(newBlock);
      await loadBlockedTimes();
      
      // Reset form
      newBlock = {
        title: '',
        start_datetime: '',
        end_datetime: '',
        recurring: false
      };
      showAddBlock = false;
      alert('✓ Blocked time added!');
    } catch (error) {
      alert('Failed to add blocked time: ' + error.message);
    }
  }
  
  async function handleDeleteBlockedTime(id) {
    if (!confirm('Delete this blocked time?')) return;
    
    try {
      await api.deleteBlockedTime(id);
      await loadBlockedTimes();
      alert('✓ Blocked time deleted!');
    } catch (error) {
      alert('Failed to delete: ' + error.message);
    }
  }
  
  function handleClose() {
    dispatch('close');
  }
  
  function formatDateTime(datetime) {
    return new Date(datetime).toLocaleString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
</script>

<div class="modal-overlay" on:click={handleClose}>
  <div class="modal-content" on:click|stopPropagation style="max-width: 700px; max-height: 85vh;">
    <div class="modal-header">
      <h3>⚙️ Calendar Settings</h3>
      <button class="btn-close" on:click={handleClose}>✕</button>
    </div>
    
    {#if loading}
      <div style="padding: 40px; text-align: center;">
        <div class="spinner"></div>
      </div>
    {:else}
      <div class="modal-body" style="max-height: calc(85vh - 140px); overflow-y: auto;">
        
        <!-- Work Hours -->
        <div class="settings-section">
          <h4>Work Hours</h4>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div>
              <label class="form-label">Start Time</label>
              <select class="form-input" bind:value={settings.work_start_hour}>
                {#each Array(24).fill(0).map((_, i) => i) as hour}
                  <option value={hour}>{hour.toString().padStart(2, '0')}:00</option>
                {/each}
              </select>
            </div>
            
            <div>
              <label class="form-label">End Time</label>
              <select class="form-input" bind:value={settings.work_end_hour}>
                {#each Array(24).fill(0).map((_, i) => i) as hour}
                  <option value={hour}>{hour.toString().padStart(2, '0')}:00</option>
                {/each}
              </select>
            </div>
          </div>
        </div>
        
        <!-- Work Schedule -->
        <div class="settings-section">
          <h4>Work Schedule</h4>
          <div style="margin-bottom: 12px;">
            <label style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; cursor: pointer;">
              <input 
                type="radio" 
                name="schedule"
                value="weekdays"
                bind:group={settings.work_schedule}
              />
              <span>Weekdays (Mon-Fri)</span>
            </label>
            
            <label style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; cursor: pointer;">
              <input 
                type="radio" 
                name="schedule"
                value="all_week"
                bind:group={settings.work_schedule}
              />
              <span>All Week (Mon-Sun)</span>
            </label>
            
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
              <input 
                type="radio" 
                name="schedule"
                value="custom"
                bind:group={settings.work_schedule}
              />
              <span>Custom Days</span>
            </label>
          </div>
          
          {#if settings.work_schedule === 'custom'}
            <div style="padding: 12px; background: #f9fafb; border-radius: 6px;">
              <label class="form-label" style="margin-bottom: 8px;">Select Days:</label>
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
                    border: 2px solid {settings.custom_days.includes(day.value) ? '#3b82f6' : '#e5e7eb'};
                    background: {settings.custom_days.includes(day.value) ? '#eff6ff' : 'white'};
                    cursor: pointer;
                    font-size: 13px;
                  ">
                    <input 
                      type="checkbox" 
                      checked={settings.custom_days.includes(day.value)}
                      on:change={(e) => {
                        const days = settings.custom_days.split(',').filter(d => d);
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
                        settings.custom_days = days.join(',');
                      }}
                      style="margin: 0;"
                    />
                    {day.label}
                  </label>
                {/each}
              </div>
            </div>
          {/if}
        </div>
        
        <!-- Lunch Break -->
        <div class="settings-section">
          <h4>Lunch Break</h4>
          <label style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; cursor: pointer;">
            <input 
              type="checkbox" 
              bind:checked={settings.lunch_break_enabled}
            />
            <span>Enable lunch break</span>
          </label>
          
          {#if settings.lunch_break_enabled}
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
              <div>
                <label class="form-label">Start Time</label>
                <input 
                  type="time" 
                  class="form-input"
                  bind:value={settings.lunch_break_start}
                />
              </div>
              
              <div>
                <label class="form-label">Duration (hours)</label>
                <input 
                  type="number" 
                  step="0.5"
                  min="0.5"
                  max="3"
                  class="form-input"
                  bind:value={settings.lunch_break_duration}
                />
              </div>
            </div>
          {/if}
        </div>
        
        <!-- Blocked Times -->
        <div class="settings-section">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h4 style="margin: 0;">Blocked Times</h4>
            <button 
              class="btn btn-sm btn-primary"
              on:click={() => showAddBlock = !showAddBlock}
            >
              {showAddBlock ? '✖️ Cancel' : '+ Add'}
            </button>
          </div>
          
          {#if showAddBlock}
            <div style="padding: 16px; background: #f9fafb; border-radius: 8px; margin-bottom: 12px;">
              <div style="margin-bottom: 12px;">
                <label class="form-label">Title</label>
                <input 
                  type="text" 
                  class="form-input"
                  bind:value={newBlock.title}
                  placeholder="e.g., Teaching, Lab Meeting, Seminar..."
                />
              </div>
              
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
                <div>
                  <label class="form-label">Start</label>
                  <input 
                    type="datetime-local" 
                    class="form-input"
                    bind:value={newBlock.start_datetime}
                  />
                </div>
                
                <div>
                  <label class="form-label">End</label>
                  <input 
                    type="datetime-local" 
                    class="form-input"
                    bind:value={newBlock.end_datetime}
                  />
                </div>
              </div>
              
              <button class="btn btn-primary" on:click={handleAddBlockedTime}>
                Add Blocked Time
              </button>
            </div>
          {/if}
          
          {#if blockedTimes.length === 0}
            <div style="padding: 20px; text-align: center; color: #9ca3af; background: #f9fafb; border-radius: 6px;">
              No blocked times set
            </div>
          {:else}
            <div style="display: flex; flex-direction: column; gap: 8px;">
              {#each blockedTimes as block}
                <div style="
                  padding: 12px;
                  background: #fef3c7;
                  border-radius: 6px;
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                ">
                  <div>
                    <div style="font-weight: 500; margin-bottom: 4px;">
                      {block.title}
                    </div>
                    <div style="font-size: 13px; color: #92400e;">
                      {formatDateTime(block.start_datetime)} - {formatDateTime(block.end_datetime)}
                    </div>
                  </div>
                  <button 
                    class="btn btn-sm btn-danger"
                    on:click={() => handleDeleteBlockedTime(block.id)}
                  >
                    Delete
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="btn btn-secondary" on:click={handleClose}>
          Cancel
        </button>
        <button class="btn btn-primary" on:click={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    {/if}
  </div>
</div>

<style>
  .settings-section {
    margin-bottom: 24px;
    padding-bottom: 24px;
    border-bottom: 1px solid #e5e7eb;
  }
  
  .settings-section:last-child {
    border-bottom: none;
  }
  
  .settings-section h4 {
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 12px 0;
    color: #1f2937;
  }
</style>
