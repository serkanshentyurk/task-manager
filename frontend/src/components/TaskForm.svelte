<script>
  import { createEventDispatcher } from 'svelte';
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
  };

  let autoSchedule = !task; // Auto-schedule new tasks by default
  let forceBump = false;
  let saving = false;

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
      if (task) {
        // Update existing task
        await api.updateTask(task.id, formData);
      } else {
        // Create new task
        if (autoSchedule) {
          await api.createTaskWithScheduling(formData, forceBump);
        } else {
          await api.createTask(formData);
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
