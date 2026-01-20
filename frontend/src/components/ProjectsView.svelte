<script>
  import { createEventDispatcher } from 'svelte';
  
  export let projects = [];
  export let tasks = [];
  export let slots = [];
  
  const dispatch = createEventDispatcher();
  
  let showCreateForm = false;
  let newProject = {
    name: '',
    colour: '#3b82f6'
  };
  
  const colors = [
    '#3b82f6', // blue
    '#10b981', // green
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // purple
    '#ec4899', // pink
    '#06b6d4', // cyan
    '#84cc16', // lime
  ];
  
  function getProjectStats(projectId) {
    const projectTasks = tasks.filter(t => t.project_id === projectId);
    const totalTasks = projectTasks.length;
    const completedTasks = projectTasks.filter(t => t.status === 'completed').length;
    
    const totalHours = projectTasks.reduce((sum, t) => sum + (t.estimated_hours || 0), 0);
    
    // Calculate scheduled hours from slots
    const projectTaskIds = projectTasks.map(t => t.id);
    const projectSlots = slots.filter(s => projectTaskIds.includes(s.task_id));
    
    let scheduledHours = 0;
    let completedHours = 0;
    
    projectSlots.forEach(slot => {
      const start = new Date(slot.start_datetime);
      const end = new Date(slot.end_datetime);
      const hours = (end - start) / (1000 * 60 * 60);
      
      scheduledHours += hours;
      if (slot.completed) {
        completedHours += hours;
      }
    });
    
    const completionPercent = totalHours > 0 ? (completedHours / totalHours) * 100 : 0;
    
    return {
      totalTasks,
      completedTasks,
      activeTasks: totalTasks - completedTasks,
      totalHours: totalHours.toFixed(1),
      scheduledHours: scheduledHours.toFixed(1),
      completedHours: completedHours.toFixed(1),
      completionPercent: completionPercent.toFixed(0)
    };
  }
  
  function getProjectTasks(projectId) {
    return tasks.filter(t => t.project_id === projectId);
  }
  
  async function handleCreateProject() {
    if (!newProject.name.trim()) {
      alert('Please enter a project name');
      return;
    }
    
    dispatch('createProject', newProject);
    
    // Reset form
    newProject = { name: '', colour: '#3b82f6' };
    showCreateForm = false;
  }
  
  function handleDeleteProject(projectId) {
    const project = projects.find(p => p.id === projectId);
    const projectTasks = tasks.filter(t => t.project_id === projectId);
    
    if (projectTasks.length > 0) {
      if (!confirm(`Delete "${project.name}"? This will unassign ${projectTasks.length} tasks from this project (tasks won't be deleted).`)) {
        return;
      }
    } else {
      if (!confirm(`Delete "${project.name}"?`)) return;
    }
    
    dispatch('deleteProject', projectId);
  }
</script>

<div style="padding: 20px; max-width: 1400px; margin: 0 auto;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
    <h1 style="font-size: 24px; font-weight: 600; margin: 0;">Projects</h1>
    <button 
      class="btn btn-primary"
      on:click={() => showCreateForm = !showCreateForm}
    >
      {showCreateForm ? '✖️ Cancel' : '+ New Project'}
    </button>
  </div>
  
  {#if showCreateForm}
    <div class="card" style="margin-bottom: 24px; padding: 20px;">
      <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600;">Create New Project</h3>
      
      <div style="display: grid; gap: 16px;">
        <div>
          <label style="display: block; margin-bottom: 4px; font-size: 13px; font-weight: 500;">
            Project Name
          </label>
          <input
            type="text"
            class="form-control"
            bind:value={newProject.name}
            placeholder="e.g., PhD Research, Lab Work, Teaching..."
            on:keydown={(e) => e.key === 'Enter' && handleCreateProject()}
          />
        </div>
        
        <div>
          <label style="display: block; margin-bottom: 8px; font-size: 13px; font-weight: 500;">
            Colour
          </label>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            {#each colors as color}
              <button
                type="button"
                style="
                  width: 40px;
                  height: 40px;
                  border-radius: 8px;
                  background: {color};
                  border: 3px solid {newProject.colour === color ? '#1f2937' : 'transparent'};
                  cursor: pointer;
                  transition: transform 0.1s;
                "
                on:click={() => newProject.colour = color}
              />
            {/each}
          </div>
        </div>
        
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-primary" on:click={handleCreateProject}>
            Create Project
          </button>
          <button class="btn btn-secondary" on:click={() => showCreateForm = false}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  {/if}
  
  {#if projects.length === 0}
    <div class="card" style="padding: 40px; text-align: center;">
      <div style="font-size: 48px; margin-bottom: 16px;">📁</div>
      <h3 style="margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">No projects yet</h3>
      <p style="color: #6b7280; margin: 0 0 20px 0;">Create your first project to organise your tasks</p>
      <button class="btn btn-primary" on:click={() => showCreateForm = true}>
        + Create Project
      </button>
    </div>
  {:else}
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px;">
      {#each projects as project}
        {@const stats = getProjectStats(project.id)}
        {@const projectTasks = getProjectTasks(project.id)}
        
        <div class="card" style="padding: 20px;">
          <!-- Project Header -->
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px;">
            <div style="flex: 1;">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <div 
                  style="
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    background: {project.colour};
                  "
                />
                <h3 style="margin: 0; font-size: 16px; font-weight: 600;">
                  {project.name}
                </h3>
              </div>
              <div style="font-size: 13px; color: #6b7280;">
                {stats.activeTasks} active • {stats.completedTasks} completed
              </div>
            </div>
            
            <button
              class="btn btn-sm btn-danger"
              on:click={() => handleDeleteProject(project.id)}
              title="Delete project"
            >
              🗑️
            </button>
          </div>
          
          <!-- Progress Bar -->
          <div style="margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;">
              <span style="font-weight: 500;">Progress</span>
              <span style="color: #6b7280;">{stats.completionPercent}%</span>
            </div>
            <div style="
              width: 100%;
              height: 8px;
              background: #e5e7eb;
              border-radius: 4px;
              overflow: hidden;
            ">
              <div style="
                width: {stats.completionPercent}%;
                height: 100%;
                background: {project.colour};
                transition: width 0.3s;
              " />
            </div>
          </div>
          
          <!-- Stats Grid -->
          <div style="
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 16px;
            padding: 12px;
            background: #f9fafb;
            border-radius: 6px;
          ">
            <div>
              <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; margin-bottom: 2px;">
                Total Hours
              </div>
              <div style="font-size: 18px; font-weight: 600;">
                {stats.totalHours}h
              </div>
            </div>
            
            <div>
              <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; margin-bottom: 2px;">
                Completed
              </div>
              <div style="font-size: 18px; font-weight: 600;">
                {stats.completedHours}h
              </div>
            </div>
            
            <div>
              <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; margin-bottom: 2px;">
                Scheduled
              </div>
              <div style="font-size: 18px; font-weight: 600;">
                {stats.scheduledHours}h
              </div>
            </div>
            
            <div>
              <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; margin-bottom: 2px;">
                Remaining
              </div>
              <div style="font-size: 18px; font-weight: 600;">
                {(parseFloat(stats.totalHours) - parseFloat(stats.completedHours)).toFixed(1)}h
              </div>
            </div>
          </div>
          
          <!-- Task List -->
          {#if projectTasks.length > 0}
            <div>
              <div style="font-size: 13px; font-weight: 500; margin-bottom: 8px; color: #6b7280;">
                Tasks ({projectTasks.length})
              </div>
              <div style="max-height: 200px; overflow-y: auto;">
                {#each projectTasks.slice(0, 5) as task}
                  <div 
                    style="
                      padding: 8px;
                      border-left: 3px solid {project.colour};
                      background: #f9fafb;
                      margin-bottom: 6px;
                      border-radius: 4px;
                      font-size: 13px;
                      cursor: pointer;
                    "
                    on:click={() => dispatch('taskClick', task)}
                  >
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <span style="font-weight: 500;">{task.title}</span>
                      <span class="badge priority-{task.priority}" style="font-size: 10px;">
                        P{task.priority}
                      </span>
                    </div>
                    {#if task.status === 'completed'}
                      <div style="color: #10b981; font-size: 11px; margin-top: 2px;">
                        ✓ Completed
                      </div>
                    {:else if task.deadline}
                      <div style="color: #6b7280; font-size: 11px; margin-top: 2px;">
                        Due: {new Date(task.deadline).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                      </div>
                    {/if}
                  </div>
                {/each}
                {#if projectTasks.length > 5}
                  <div style="text-align: center; padding: 8px; color: #6b7280; font-size: 12px;">
                    +{projectTasks.length - 5} more tasks
                  </div>
                {/if}
              </div>
            </div>
          {:else}
            <div style="
              padding: 20px;
              text-align: center;
              background: #f9fafb;
              border-radius: 6px;
              color: #6b7280;
              font-size: 13px;
            ">
              No tasks in this project yet
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
