<script>
  export let stats = {};

  $: taskStats = stats.tasks || {};
  $: byStatus = taskStats.by_status || {};
  $: byPriority = taskStats.by_priority || {};
  $: upcomingDeadlines = stats.upcoming_deadlines || [];
</script>

<div class="card">
  <div class="card-header">
    Dashboard
  </div>

  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
    <!-- Task counts -->
    <div style="padding: 12px; background: #eff6ff; border-radius: 6px;">
      <div class="text-sm text-gray-500">Total Tasks</div>
      <div style="font-size: 24px; font-weight: 700; color: #3b82f6;">
        {taskStats.total || 0}
      </div>
    </div>

    <div style="padding: 12px; background: #fef3c7; border-radius: 6px;">
      <div class="text-sm text-gray-500">In Progress</div>
      <div style="font-size: 24px; font-weight: 700; color: #f59e0b;">
        {byStatus.in_progress || 0}
      </div>
    </div>

    <div style="padding: 12px; background: #d1fae5; border-radius: 6px;">
      <div class="text-sm text-gray-500">Completed</div>
      <div style="font-size: 24px; font-weight: 700; color: #10b981;">
        {byStatus.completed || 0}
      </div>
    </div>

    <div style="padding: 12px; background: #fee2e2; border-radius: 6px;">
      <div class="text-sm text-gray-500">High Priority</div>
      <div style="font-size: 24px; font-weight: 700; color: #ef4444;">
        {(byPriority[4] || 0) + (byPriority[5] || 0)}
      </div>
    </div>
  </div>

  {#if upcomingDeadlines.length > 0}
    <div style="margin-top: 20px;">
      <div style="font-weight: 600; margin-bottom: 12px; color: #6b7280;">
        📅 Upcoming Deadlines (Next 7 Days)
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        {#each upcomingDeadlines as task}
          <div style="padding: 8px 12px; background: #f9fafb; border-radius: 6px; border-left: 3px solid {task.priority >= 4 ? '#ef4444' : '#3b82f6'};">
            <div style="font-weight: 500;">{task.title}</div>
            <div class="text-xs text-gray-500">
              {new Date(task.deadline).toLocaleDateString()} • Priority: {'🔴'.repeat(task.priority)}
              {#if task.project_name}
                • {task.project_name}
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
