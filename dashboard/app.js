/* ================================================================
   FlowBoard — 多项目任务看板
   GitHub Backlog 风格 · 5列状态 · 项目选择器 · AI对接接口
   ================================================================ */
'use strict';

// ─────────────────────────────────────────────────────────────
// 0. COMPANY PROJECTS — AI设计工作流作为其中一个母项
// ─────────────────────────────────────────────────────────────
const COMPANY_PROJECTS = [
  {
    id: 'ai-design',
    name: 'AI 空间设计工作流',
    shortName: 'AI设计',
    desc: '800㎡ 展厅 · 12阶段工作流',
    color: '#1f6feb',
    isActive: true,          // 当前选中
    isCurrent: true,         // 当前项目（母项）
    taskCount: 12,
  },
  {
    id: 'brand-renewal',
    name: '品牌视觉升级项目',
    shortName: '品牌升级',
    desc: 'VI体系 · 品牌设计',
    color: '#bc8cff',
    isActive: false,
    isCurrent: false,
    taskCount: 8,
  },
  {
    id: 'digital-twin',
    name: '数字孪生展示系统',
    shortName: '数字孪生',
    desc: '实时数据 · 3D可视化',
    color: '#3fb950',
    isActive: false,
    isCurrent: false,
    taskCount: 6,
  },
  {
    id: 'client-portal',
    name: '客户协作门户',
    shortName: '客户门户',
    desc: '方案审批 · 意见反馈',
    color: '#f0883e',
    isActive: false,
    isCurrent: false,
    taskCount: 5,
  },
];

let activeProjectId = 'ai-design';
// 优先从本地 server.py API 读取（port 8765），回退到文件路径
const API_BASE = 'http://localhost:8765';
const CURRENT_BOARD_URL = `${API_BASE}/boards/current`;
const BOARD_INDEX_URL   = `${API_BASE}/boards`;
let currentBoard = null;
let currentBoardIndex = null;
let boardSnapshotMode = false;

// ─────────────────────────────────────────────────────────────
// 1. LEADERS & TASKS (AI设计工作流 · 4中项 × 12子项)
// ─────────────────────────────────────────────────────────────
const LEADERS = [
  { id: 'research', name: 'ResearchLeader', abbr: 'Research', icon: '🔍', color: '#60a5fa', desc: '信息采集组', badgeClass: 'badge-research' },
  { id: 'creative', name: 'CreativeLeader', abbr: 'Creative', icon: '🎨', color: '#c084fc', desc: '创意设计组', badgeClass: 'badge-creative' },
  { id: 'tech',     name: 'TechLeader',     abbr: 'Tech',     icon: '⚙️', color: '#34d399', desc: '技术实现组', badgeClass: 'badge-tech' },
  { id: 'pm',       name: 'PMLeader',       abbr: 'PM',       icon: '📋', color: '#fb923c', desc: '项目管理组', badgeClass: 'badge-pm' },
];

const TASKS_INIT = [
  // ── ResearchLeader ──
  { id:'SP-001', name:'需求解析',      leader:'research', seq:1,  isMvp:true,  isStub:false, skill:'req_parser',    tools:['parse_brief','extract_constraints','validate_requirements'], rules:['面积字段必须明确（默认800㎡）','受众必须区分主/次两类','禁止直接生成设计方案'], input:'client_brief (string)', output:'structured_brief { area, audience, style_preference }', status:'backlog', events:[] },
  { id:'SP-002', name:'案例研究',      leader:'research', seq:2,  isMvp:false, isStub:false, skill:'case_research', tools:['wiki_query','case_search','case_summarize','extract_highlights'], rules:['搜索前注入4字段提取意图','wiki命中优先引用'], input:'structured_brief', output:'case_analysis [ { name, area, style, highlights } × 3 ]', status:'backlog', events:[] },
  // ── CreativeLeader ──
  { id:'SP-003', name:'概念提炼',      leader:'creative', seq:3,  isMvp:false, isStub:true,  skill:'concept',       tools:['concept_generate','keyword_extract','moodboard_suggest'], rules:['概念描述字数限制：每条≤80字'], input:'structured_brief + case_analysis', output:'{ theme, concepts[3], moodboard_keywords }', status:'backlog', events:[] },
  { id:'SP-004', name:'空间故事线',    leader:'creative', seq:4,  isMvp:false, isStub:true,  skill:'storyline',     tools:['storyline_draft','narrative_check','flow_optimize'], rules:['动线必须覆盖所有功能分区'], input:'concept', output:'{ route, zone_narratives, emotion_curve }', status:'backlog', events:[] },
  { id:'SP-005', name:'功能分区',      leader:'creative', seq:5,  isMvp:false, isStub:true,  skill:'zoning',        tools:['zone_suggest','area_calculator','adjacency_check'], rules:['zone_suggest前注入面积约束（总计≤800㎡）'], input:'storyline', output:'zones [ { name, area, function } × 6 ]', status:'backlog', events:[] },
  { id:'SP-006', name:'材料色彩风格',  leader:'creative', seq:6,  isMvp:true,  isStub:false, skill:'material_style',tools:['get_design_spec','style_generate','color_palette','material_spec','wiki_update'], rules:['输出格式必须含HEX色值','PostToolUse触发wiki_update'], input:'structured_brief + zoning', output:'{ styles[3], hex_colors, material_spec }', status:'backlog', events:[] },
  // ── TechLeader ──
  { id:'SP-007', name:'效果图 Prompt', leader:'tech',     seq:7,  isMvp:true,  isStub:false, skill:'visual_prompt', tools:['get_design_spec','prompt_compose','style_inject','quality_enhance'], rules:['从DESIGN.md Agent Prompt Guide取模板'], input:'material_spec', output:'visual_prompts { zone → prompt_string }', status:'backlog', events:[] },
  { id:'SP-008', name:'视频脚本',      leader:'tech',     seq:8,  isMvp:false, isStub:true,  skill:'video_script',  tools:['script_draft','scene_sequence','duration_calc'], rules:['总时长3min'], input:'visual_prompts', output:'video_script { scenes, duration, narration }', status:'backlog', events:[] },
  { id:'SP-009', name:'造价预算',      leader:'tech',     seq:9,  isMvp:false, isStub:true,  skill:'cost_estimate', tools:['wiki_query','cost_llm_estimate','budget_breakdown'], rules:['cost_estimate前注入材料规格表'], input:'material_spec', output:'cost_estimate { breakdown, total_range }', status:'backlog', events:[] },
  // ── PMLeader ──
  { id:'SP-010', name:'汇报整理',      leader:'pm',       seq:10, isMvp:false, isStub:true,  skill:'report',        tools:['summary_write','slide_outline','table_format'], rules:['必须包含4章节：背景/方案/造价/时间线'], input:'full_context', output:'{ report_outline, executive_summary }', status:'backlog', events:[] },
  { id:'SP-011', name:'客户反馈修改',  leader:'pm',       seq:11, isMvp:false, isStub:true,  skill:'feedback',      tools:['parse_feedback','impact_analysis','patch_output'], rules:['禁止触发全量重跑'], input:'client_feedback (string)', output:'{ affected_stages, feedback_patch }', status:'backlog', events:[] },
  { id:'SP-012', name:'进度管理',      leader:'pm',       seq:12, isMvp:false, isStub:true,  skill:'progress',      tools:['task_breakdown','timeline_generate','milestone_set'], rules:['里程碑数量约束：3-5个'], input:'full_context', output:'{ milestones[3-5], task_list }', status:'backlog', events:[] },
];

// Column config — 5列 GitHub Backlog 风格
const COLUMNS = [
  { status:'backlog',  label:'Backlog',     color:'var(--c-backlog)', subtitle:'This item hasn\'t been started',     icon:'○' },
  { status:'ready',    label:'Ready',       color:'var(--c-ready)',   subtitle:'This is ready to be picked up',       icon:'◉' },
  { status:'doing',    label:'In progress', color:'var(--c-doing)',   subtitle:'This is actively being worked on',    icon:'◐' },
  { status:'review',   label:'In review',   color:'var(--c-review)',  subtitle:'This item is in review',              icon:'◑' },
  { status:'done',     label:'Done',        color:'var(--c-done)',    subtitle:'This has been completed',             icon:'●' },
];

const STATUS_OPTS = [
  { value:'backlog', label:'Backlog',     cls:'s-backlog' },
  { value:'ready',   label:'Ready',       cls:'s-ready' },
  { value:'doing',   label:'In progress', cls:'s-doing' },
  { value:'review',  label:'In review',   cls:'s-review' },
  { value:'done',    label:'Done',        cls:'s-done' },
  { value:'blocked', label:'Blocked',     cls:'s-blocked' },
];

// ─────────────────────────────────────────────────────────────
// 2. TASK MANAGEMENT API
// ─────────────────────────────────────────────────────────────
const TaskAPI = (() => {
  const KEY = 'flowboard_tasks_v1';
  let tasks = [];
  let listeners = [];

  function save() { localStorage.setItem(KEY, JSON.stringify(tasks)); }
  function load() {
    try {
      const s = localStorage.getItem(KEY);
      tasks = s ? JSON.parse(s) : deep(TASKS_INIT);
    } catch { tasks = deep(TASKS_INIT); }
  }
  function deep(o) { return JSON.parse(JSON.stringify(o)); }
  function notify(ev, payload) { listeners.forEach(fn => fn(ev, payload)); }

  return {
    init() { load(); },
    reset() { tasks = deep(TASKS_INIT); save(); notify('reset', {}); },
    hydrate(nextTasks) {
      tasks = deep(nextTasks);
      notify('hydrated', { count: tasks.length });
    },

    getTasks(filter = {}) {
      let r = [...tasks];
      if (filter.leader) r = r.filter(t => t.leader === filter.leader);
      if (filter.status) r = r.filter(t => t.status === filter.status);
      if (filter.search) {
        const q = filter.search.toLowerCase();
        r = r.filter(t =>
          t.name.toLowerCase().includes(q)   ||
          t.id.toLowerCase().includes(q)     ||
          t.skill.toLowerCase().includes(q)  ||
          (t.input  || '').toLowerCase().includes(q) ||
          (t.output || '').toLowerCase().includes(q) ||
          (t.rules  || []).some(rule => rule.toLowerCase().includes(q)) ||
          (t.tools  || []).some(tool => tool.toLowerCase().includes(q))
        );
      }
      return r;
    },

    getTask(id) { return tasks.find(t => t.id === id) || null; },

    updateStatus(id, status) {
      if (boardSnapshotMode) return { error: 'READ_ONLY' };
      const t = tasks.find(t => t.id === id);
      if (!t) return { error: 'NOT_FOUND' };
      const old = t.status;
      t.status = status;
      t.events.push({ time: now(), text: `状态: ${old} → ${status}` });
      save();
      notify('status_changed', { id, old, status });
      AIBus.emit('task.status', { id, name: t.name, from: old, to: status });
      return { ok: true, task: t };
    },

    triggerSkill(id) {
      if (boardSnapshotMode) return { error: 'READ_ONLY' };
      const t = tasks.find(t => t.id === id);
      if (!t) return { error: 'NOT_FOUND' };
      const old = t.status;
      t.status = 'doing';
      t.events.push({ time: now(), text: `Skill触发: ${t.skill}` });
      save();
      notify('skill_triggered', { id, skill: t.skill });
      AIBus.emit('tool.call', { agent: t.skill, tool: t.tools[0], status: 'triggered' });

      setTimeout(() => {
        const t2 = tasks.find(x => x.id === id);
        if (t2 && t2.status === 'doing') {
          t2.status = 'done';
          t2.events.push({ time: now(), text: `Skill完成: ${t2.skill}` });
          save();
          notify('skill_done', { id, skill: t2.skill });
          AIBus.emit('task.status', { id, name: t2.name, from: 'doing', to: 'done' });
          updateProgress();
          renderBoard();
          renderList();
          renderSubtaskNav();
        }
      }, 2000 + Math.random() * 1200);

      return { ok: true, task: t };
    },

    getStats() {
      const total = tasks.length;
      const done  = tasks.filter(t => t.status === 'done').length;
      const doing = tasks.filter(t => t.status === 'doing').length;
      return { total, done, doing, pct: Math.round(done / total * 100) };
    },

    on(fn) { listeners.push(fn); },
  };
})();

// ─────────────────────────────────────────────────────────────
// 3. AI EVENT BUS
// ─────────────────────────────────────────────────────────────
const AIBus = (() => {
  const SIG_KEY = 'flowboard_signals';
  let handlers = {};
  let log = [];
  let traceId = null;
  let status = 'idle';

  return {
    newTrace() {
      traceId = 'tr-' + Math.random().toString(36).slice(2,10) + '-' + Date.now().toString(36);
      const el1 = document.getElementById('currentTrace');
      if (el1) el1.textContent = traceId;
      return traceId;
    },
    getTraceId() { return traceId; },
    getStatus()  { return status; },

    emit(topic, payload) {
      const ev = {
        event_id:  'ev-' + Math.random().toString(36).slice(2,8),
        trace_id:  traceId || '—',
        timestamp: now(),
        topic,
        event_type: topic.replace('.','_'),
        producer:  payload.agent || payload.id || 'system',
        payload,
      };
      log.unshift(ev);
      if (log.length > 500) log.pop();
      appendStreamLine(ev);
      appendLogEntry(ev);
      if (handlers[topic]) handlers[topic].forEach(fn => fn(ev));
      return ev;
    },

    on(topic, fn) { if (!handlers[topic]) handlers[topic] = []; handlers[topic].push(fn); },
    getLogs(f) { return (!f || f === 'all') ? log : log.filter(e => e.topic === f); },
    clearLogs() { log = []; },
    hydrate(nextLog, nextTraceId, nextStatus = 'idle') {
      log = Array.isArray(nextLog) ? [...nextLog] : [];
      traceId = nextTraceId || traceId;
      status = nextStatus;
      const el1 = document.getElementById('currentTrace');
      if (el1) el1.textContent = traceId || '—';
    },

    pause()  { status = 'paused';    setAgent('running','已暂停'); this.emit('task.status',{signal:'pause'}); writeSignal('pause');  toast('⏸ Pause 信号已发送','warn'); },
    resume() { status = 'running';   setAgent('running','运行中'); this.emit('task.status',{signal:'resume'}); writeSignal('resume'); toast('▶ Resume 信号已发送','success'); },
    cancel() { status = 'cancelled'; setAgent('idle','已取消');   this.emit('task.status',{signal:'cancel'}); writeSignal('cancel'); toast('✕ Cancel 信号已发送','info'); },

    async runMVP() {
      this.newTrace(); status = 'running'; setAgent('running','MVP 执行中...');
      this.emit('task.status',{agent:'orchestrator',state:'MVP Start'});
      toast('▶ MVP 流程启动','success');
      for (const step of [{id:'SP-001',d:800},{id:'SP-006',d:1600},{id:'SP-007',d:1400}]) {
        await sleep(step.d);
        if (status === 'cancelled') break;
        while (status === 'paused') await sleep(200);
        TaskAPI.triggerSkill(step.id);
        updateProgress();
      }
      await sleep(2500);
      if (status !== 'cancelled') { status = 'idle'; setAgent('done','MVP 完成'); toast('✦ MVP 执行完成！','success'); }
    },

    async runDemo() {
      this.newTrace(); status = 'running'; setAgent('running','Demo 执行中...');
      this.emit('task.status',{agent:'orchestrator',state:'Demo Start'});
      toast('⬡ 全流程 Demo 启动','info');
      for (const id of TaskAPI.getTasks().sort((a,b)=>a.seq-b.seq).map(t=>t.id)) {
        await sleep(500 + Math.random()*300);
        if (status === 'cancelled') break;
        while (status === 'paused') await sleep(200);
        TaskAPI.triggerSkill(id);
        updateProgress();
      }
      await sleep(800);
      if (status !== 'cancelled') { status = 'idle'; setAgent('done','Demo 完成'); toast('⬡ Demo 执行完成！','success'); }
    },
  };

  function writeSignal(sig) {
    const arr = JSON.parse(localStorage.getItem(SIG_KEY)||'[]');
    arr.push({trace_id:traceId,signal:sig,timestamp:now()});
    localStorage.setItem(SIG_KEY,JSON.stringify(arr.slice(-20)));
  }
})();

// ─────────────────────────────────────────────────────────────
// 4. PROJECT SELECTOR
// ─────────────────────────────────────────────────────────────
function renderProjectSelector() {
  const proj = COMPANY_PROJECTS.find(p => p.id === activeProjectId) || COMPANY_PROJECTS[0];

  // Topbar breadcrumb
  const bcProj = document.getElementById('bcProject');
  if (bcProj) bcProj.textContent = proj.name;

  // Sidebar current
  const dot  = document.getElementById('projectDot');
  const name = document.getElementById('projectCurrentName');
  if (dot)  { dot.style.background = proj.color; }
  if (name) { name.textContent = proj.name; }

  // Dropdown
  const dd = document.getElementById('projectDropdown');
  if (!dd) return;
  dd.innerHTML = `<div class="proj-dropdown-header">公司项目</div>`;

  COMPANY_PROJECTS.forEach(p => {
    const item = document.createElement('div');
    item.className = 'proj-item' + (p.id === activeProjectId ? ' active' : '');
    item.innerHTML = `
      <span class="proj-item-dot" style="background:${p.color}"></span>
      <div class="proj-item-info">
        <div class="proj-item-name">${p.name}</div>
        <div class="proj-item-sub">${p.desc} · ${p.taskCount} 任务</div>
      </div>
      ${p.id === activeProjectId ? '<span class="proj-item-check">✓</span>' : ''}
    `;
    item.addEventListener('click', () => {
      activeProjectId = p.id;
      // 关闭下拉
      document.getElementById('projectSelector').classList.remove('open');
      renderProjectSelector();
      renderSubtaskNav();
      if (p.id === 'ai-design') {
        // 已有真实数据
        renderBoard();
        renderList();
        updateProgress();
        toast(`已切换到: ${p.name}`, 'info');
      } else {
        // 其他项目显示空看板提示
        renderBoardEmpty(p);
        toast(`已切换到: ${p.name}（示例项目）`, 'info');
      }
    });
    dd.appendChild(item);
  });
}

function initProjectSelector() {
  const trigger = document.getElementById('projectCurrent');
  const selector = document.getElementById('projectSelector');
  if (!trigger) return;
  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    selector.classList.toggle('open');
  });
  document.addEventListener('click', () => selector.classList.remove('open'));
  renderProjectSelector();
}

// ─────────────────────────────────────────────────────────────
// 5. SUBTASK NAV (12 Specialists 在侧边栏)
// ─────────────────────────────────────────────────────────────
function renderSubtaskNav() {
  const nav = document.getElementById('subtaskNav');
  if (!nav) return;
  nav.innerHTML = '';

  if (activeProjectId !== 'ai-design') {
    nav.innerHTML = '<div style="padding:4px 10px;font-size:11px;color:var(--text-3)">（其他项目子任务）</div>';
    return;
  }

  TaskAPI.getTasks().sort((a,b)=>a.seq-b.seq).forEach(task => {
    const leader = LEADERS.find(l => l.id === task.leader);
    const colMeta = getColMeta(task.status);
    const item = document.createElement('div');
    item.className = 'subtask-item';
    item.innerHTML = `
      <span class="subtask-status-dot" style="background:${colMeta.color}"></span>
      <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${task.name}</span>
      <span class="subtask-id">${task.id}</span>
    `;
    item.title = `${task.id} · ${task.name} · ${colMeta.label}`;
    item.addEventListener('click', () => openDrawer(task.id));
    nav.appendChild(item);
  });
}

function getColMeta(status) {
  const map = {
    backlog:  { color: '#6e7681', label: 'Backlog' },
    ready:    { color: '#58a6ff', label: 'Ready' },
    doing:    { color: '#f0883e', label: 'In progress' },
    review:   { color: '#bc8cff', label: 'In review' },
    done:     { color: '#3fb950', label: 'Done' },
    blocked:  { color: '#f85149', label: 'Blocked' },
    cancelled:{ color: '#6e7681', label: 'Cancelled' },
  };
  return map[status] || map.backlog;
}

// ─────────────────────────────────────────────────────────────
// 6. BOARD RENDER
// ─────────────────────────────────────────────────────────────
function renderBoard(searchQ = '') {
  const wrap = document.getElementById('boardWrap');
  if (!wrap) return;
  wrap.innerHTML = '';

  const proj = COMPANY_PROJECTS.find(p => p.id === activeProjectId);
  if (!proj) return;

  if (activeProjectId !== 'ai-design') {
    renderBoardEmpty(proj);
    return;
  }

  COLUMNS.forEach(col => {
    const tasks = TaskAPI.getTasks({ status: col.status, search: searchQ || undefined });

    const colEl = document.createElement('div');
    colEl.className = 'board-col';
    colEl.innerHTML = `
      <div class="col-header">
        <span class="col-status-dot" style="background:${col.color}"></span>
        <div class="col-label-wrap">
          <div class="col-label">
            ${col.label}
            <span class="col-count">${tasks.length}</span>
          </div>
          <div class="col-subtitle">${col.subtitle}</div>
        </div>
      </div>
      <div class="col-body" id="col-${col.status}"></div>
      <div class="col-add">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        Add item
      </div>
    `;
    wrap.appendChild(colEl);
  });

  TaskAPI.getTasks({ search: searchQ || undefined }).forEach(task => {
    const colBody = document.getElementById(`col-${task.status}`);
    if (colBody) colBody.appendChild(makeCard(task));
  });
}

function renderBoardEmpty(proj) {
  const wrap = document.getElementById('boardWrap');
  if (!wrap) return;
  wrap.innerHTML = '';

  // Show placeholder columns
  COLUMNS.forEach(col => {
    const colEl = document.createElement('div');
    colEl.className = 'board-col';
    colEl.innerHTML = `
      <div class="col-header">
        <span class="col-status-dot" style="background:${col.color}"></span>
        <div class="col-label-wrap">
          <div class="col-label">${col.label} <span class="col-count">0</span></div>
          <div class="col-subtitle">${col.subtitle}</div>
        </div>
      </div>
      <div class="col-body" style="align-items:center;justify-content:center;padding-top:40px">
        <div style="text-align:center;color:var(--text-3);font-size:12px">
          <div style="font-size:24px;margin-bottom:8px">○</div>
          <div>暂无任务</div>
          <div style="font-size:11px;margin-top:4px">${proj.name}</div>
        </div>
      </div>
      <div class="col-add">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        Add item
      </div>
    `;
    wrap.appendChild(colEl);
  });
}

function makeCard(task) {
  const leader = LEADERS.find(l => l.id === task.leader);
  const card = document.createElement('div');
  const colMeta = getColMeta(task.status);
  card.className = `task-card${task.status === 'doing' ? ' is-doing' : ''}${task.status === 'review' ? ' is-review' : ''}${task.status === 'done' ? ' is-done' : ''}`;
  card.dataset.id = task.id;

  const proj = COMPANY_PROJECTS.find(p => p.id === activeProjectId);
  const prefix = proj ? `${proj.shortName} #${task.seq}` : task.id;

  card.innerHTML = `
    <div class="card-top">
      <span class="card-project-prefix">${prefix}</span>
      <span class="card-title">${task.name}</span>
      <div class="card-actions">
        <button class="card-action-btn" title="触发 Skill" data-trigger="${task.id}">▶</button>
        <button class="card-action-btn" title="详情" data-detail="${task.id}">···</button>
      </div>
    </div>
    <div class="card-badges">
      ${task.isMvp  ? '<span class="badge badge-mvp">MVP</span>' : ''}
      ${task.isStub ? '<span class="badge badge-stub">Stub</span>' : ''}
      ${leader ? `<span class="badge ${leader.badgeClass}">${leader.abbr}</span>` : ''}
    </div>
    <div class="card-footer">
      <span class="card-id">${task.id}</span>
      <span class="card-skill">${task.skill}</span>
      <span class="card-subtask-count">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none"><path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        ${task.tools.length}
      </span>
      <div class="card-avatar" style="background:${leader ? leader.color + '22' : 'var(--bg-3)'}; color:${leader ? leader.color : 'var(--text-3)'}">
        ${leader ? leader.icon : '?'}
      </div>
    </div>
  `;

  card.querySelector(`[data-trigger]`)?.addEventListener('click', e => {
    e.stopPropagation();
    if (AIConnector.isConfigured()) {
      switchView('ai');
      setTimeout(() => runRealSkill(task.id), 100);
      toast(`▶ 真实 LLM: ${task.skill}`, 'info');
    } else {
      TaskAPI.triggerSkill(task.id);
      updateProgress();
      renderBoard();
      renderList();
      renderSubtaskNav();
      toast(`✦ Mock: ${task.skill}`, 'info');
    }
  });

  card.addEventListener('click', () => openDrawer(task.id));
  return card;
}

// ─────────────────────────────────────────────────────────────
// 7. LIST VIEW
// ─────────────────────────────────────────────────────────────
function renderList(searchQ = '') {
  const wrap = document.getElementById('listWrap');
  if (!wrap) return;
  wrap.innerHTML = '';

  if (activeProjectId !== 'ai-design') {
    wrap.innerHTML = `<div style="padding:40px;text-align:center;color:var(--text-3)">请切换到 AI 空间设计工作流项目查看列表</div>`;
    return;
  }

  LEADERS.forEach(leader => {
    const tasks = TaskAPI.getTasks({ leader: leader.id, search: searchQ || undefined });
    if (tasks.length === 0) return;

    const group = document.createElement('div');
    group.className = 'list-group';
    group.innerHTML = `
      <div class="list-group-hd">
        <span>${leader.icon}</span>
        <span class="list-group-name" style="color:${leader.color}">${leader.name}</span>
        <span style="color:var(--text-3);font-size:11px">${leader.desc}</span>
        <span class="list-group-count">${tasks.length} 个子任务</span>
      </div>
      <div class="list-header">
        <span>ID</span><span>名称</span><span>状态</span><span>Leader</span><span>MVP</span><span>Skill</span>
      </div>
    `;

    tasks.forEach(task => {
      const sm = STATUS_OPTS.find(s => s.value === task.status) || STATUS_OPTS[0];
      const row = document.createElement('div');
      row.className = 'list-row';
      row.innerHTML = `
        <span class="list-cell list-cell-id">${task.id}</span>
        <span class="list-cell list-cell-name">${task.name}</span>
        <span class="list-cell"><span class="status-badge ${sm.cls}">${sm.label}</span></span>
        <span class="list-cell" style="color:${leader.color}">${leader.abbr}</span>
        <span class="list-cell">${task.isMvp ? '<span class="badge badge-mvp">MVP</span>' : task.isStub ? '<span class="badge badge-stub">Stub</span>' : '—'}</span>
        <span class="list-cell list-cell-skill">${task.skill}</span>
      `;
      row.addEventListener('click', () => openDrawer(task.id));
      group.appendChild(row);
    });

    wrap.appendChild(group);
  });
}

// ─────────────────────────────────────────────────────────────
// 8. TIMELINE VIEW
// ─────────────────────────────────────────────────────────────
function renderTimeline() {
  const wrap = document.getElementById('timelineWrap');
  if (!wrap) return;
  wrap.innerHTML = '';

  const hdr = document.createElement('div');
  hdr.style.cssText = 'padding:16px 20px 8px;font-size:13px;font-weight:600;color:var(--text-2);border-bottom:1px solid var(--border);flex-shrink:0';
  hdr.textContent = '时间线 — 12 个子任务执行顺序';
  wrap.appendChild(hdr);

  const body = document.createElement('div');
  body.style.cssText = 'padding:12px 20px;';

  TaskAPI.getTasks().sort((a,b)=>a.seq-b.seq).forEach((task, idx) => {
    const leader = LEADERS.find(l => l.id === task.leader);
    const sm = STATUS_OPTS.find(s => s.value === task.status) || STATUS_OPTS[0];
    const filled = task.status === 'done' ? 100 : task.status === 'doing' ? 50 : task.status === 'review' ? 75 : task.status === 'ready' ? 15 : 0;
    const barColor = task.isMvp ? 'var(--c-done)' : leader ? leader.color : '#6b7280';
    const trackW = Math.floor(100 / 12 * (idx + 1));

    const row = document.createElement('div');
    row.className = 'tl-row';
    row.innerHTML = `
      <div class="tl-label">
        <div class="tl-id">${task.id}</div>
        <div class="tl-name">${task.name}</div>
      </div>
      <div class="tl-track" style="background:var(--bg-2)">
        <div class="tl-bar-fill" style="width:${filled}%;background:${barColor}">
          <span class="tl-bar-label">${filled > 10 ? task.name : ''}</span>
        </div>
      </div>
      <div class="tl-status">
        <span class="status-badge ${sm.cls}">${sm.label}</span>
      </div>
    `;
    row.addEventListener('click', () => openDrawer(task.id));
    body.appendChild(row);
  });

  wrap.appendChild(body);
}

// ─────────────────────────────────────────────────────────────
// 9. AI CONNECTOR — 真实 LLM 接口对接
// ─────────────────────────────────────────────────────────────
const AIConnector = (() => {
  const CFG_KEY = 'flowboard_ai_cfg';

  const PROVIDER_DEFAULTS = {
    openai:   { baseUrl: 'https://api.openai.com/v1',                    model: 'gpt-4o' },
    zhipu:    { baseUrl: 'https://open.bigmodel.cn/api/paas/v4',         model: 'glm-4-flash' },
    deepseek: { baseUrl: 'https://api.deepseek.com/v1',                  model: 'deepseek-chat' },
    qwen:     { baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-turbo' },
    custom:   { baseUrl: '', model: '' },
  };

  let cfg = { provider: 'openai', baseUrl: '', model: '', apiKey: '' };

  function load() {
    try { const s = localStorage.getItem(CFG_KEY); if (s) cfg = { ...cfg, ...JSON.parse(s) }; } catch {}
  }
  function save() { localStorage.setItem(CFG_KEY, JSON.stringify(cfg)); }

  function isConfigured() { return !!(cfg.apiKey && cfg.apiKey.length > 6); }

  function getEndpoint() {
    const base = cfg.baseUrl || PROVIDER_DEFAULTS[cfg.provider]?.baseUrl || '';
    return base.replace(/\/$/, '') + '/chat/completions';
  }

  function getModel() {
    return cfg.model || PROVIDER_DEFAULTS[cfg.provider]?.model || 'gpt-4o';
  }

  // 构建 Skill Prompt
  function buildPrompt(task) {
    return [
      `你是一个 AI 空间设计工作流的 Skill 执行器。`,
      `当前任务: [${task.id}] ${task.name}`,
      `所属 Leader: ${task.leader}`,
      `Skill: ${task.skill}`,
      `可用工具: ${task.tools.join(', ')}`,
      `策略规则: ${task.rules.join('; ')}`,
      `输入格式: ${task.input}`,
      `期望输出: ${task.output}`,
      ``,
      `请模拟执行该 Skill，输出结构化结果（JSON）并附上简要执行说明。`,
      `输出语言：中文，JSON 字段名用英文。`,
    ].join('\n');
  }

  // 流式调用（SSE fetch）
  async function callStream(task, onToken, onDone, onError) {
    const endpoint = getEndpoint();
    const model    = getModel();
    const prompt   = buildPrompt(task);

    AIBus.emit('tool.call', { agent: task.skill, tool: 'llm_call', model, endpoint: endpoint.replace(/\/\/.*?@/, '//***@') });

    let fullText = '';
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${cfg.apiKey}`,
        },
        body: JSON.stringify({
          model,
          stream: true,
          messages: [
            { role: 'system', content: '你是一个高效的 AI 工作流执行器，输出简洁、结构化。' },
            { role: 'user',   content: prompt },
          ],
          max_tokens: 800,
          temperature: 0.3,
        }),
      });

      if (!resp.ok) {
        const errText = await resp.text().catch(() => resp.statusText);
        throw new Error(`HTTP ${resp.status}: ${errText.slice(0, 120)}`);
      }

      const reader  = resp.body.getReader();
      const decoder = new TextDecoder();
      let   buf     = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop();
        for (const line of lines) {
          const trimmed = line.replace(/^data:\s*/, '');
          if (!trimmed || trimmed === '[DONE]') continue;
          try {
            const chunk = JSON.parse(trimmed);
            const token = chunk.choices?.[0]?.delta?.content || '';
            if (token) { fullText += token; onToken(token); }
          } catch {}
        }
      }
      onDone(fullText);
    } catch (err) {
      onError(err.message || String(err));
    }
  }

  // 非流式 fallback（用于测试连接）
  async function testConnection() {
    const endpoint = getEndpoint();
    const model    = getModel();
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${cfg.apiKey}` },
        body: JSON.stringify({
          model, stream: false,
          messages: [{ role: 'user', content: 'ping' }],
          max_tokens: 5,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  }

  return {
    load, save,
    isConfigured,
    getModel,
    getEndpoint,
    getCfg() { return cfg; },
    updateCfg(patch) { cfg = { ...cfg, ...patch }; },
    callStream,
    testConnection,
    PROVIDER_DEFAULTS,
  };
})();

// ─────────────────────────────────────────────────────────────
// 10. AI PANEL
// ─────────────────────────────────────────────────────────────
function renderAIPanel() {
  // ── 配置区 UI 绑定（只绑一次）
  const provider = document.getElementById('cfgProvider');
  const model    = document.getElementById('cfgModel');
  const baseUrl  = document.getElementById('cfgBaseUrl');
  const apiKey   = document.getElementById('cfgApiKey');

  if (provider && !provider._bound) {
    provider._bound = true;

    // 读取已保存配置
    const cfg = AIConnector.getCfg();
    provider.value = cfg.provider || 'openai';
    model.value    = cfg.model    || '';
    baseUrl.value  = cfg.baseUrl  || '';
    apiKey.value   = cfg.apiKey   ? '•'.repeat(Math.min(cfg.apiKey.length, 24)) : '';

    provider.addEventListener('change', () => {
      const def = AIConnector.PROVIDER_DEFAULTS[provider.value];
      if (def) {
        if (!model.value || model.value === AIConnector.PROVIDER_DEFAULTS[provider._prev]?.model)
          model.value = def.model;
        baseUrl.placeholder = def.baseUrl;
      }
      provider._prev = provider.value;
    });
    provider._prev = provider.value;
    // 初始 placeholder
    baseUrl.placeholder = AIConnector.PROVIDER_DEFAULTS[provider.value]?.baseUrl || '';

    document.getElementById('btnSaveCfg')?.addEventListener('click', () => {
      const keyVal = apiKey.value.startsWith('•') ? AIConnector.getCfg().apiKey : apiKey.value.trim();
      AIConnector.updateCfg({
        provider: provider.value,
        model:    model.value.trim(),
        baseUrl:  baseUrl.value.trim(),
        apiKey:   keyVal,
      });
      AIConnector.save();
      updateConfigStatus(true);
      toast('✓ 配置已保存', 'success');
    });

    document.getElementById('btnTestConn')?.addEventListener('click', async () => {
      const tip = document.getElementById('cfgTip');
      tip.textContent = '正在测试连接...';
      tip.style.color = 'var(--text-2)';
      const keyVal = apiKey.value.startsWith('•') ? AIConnector.getCfg().apiKey : apiKey.value.trim();
      AIConnector.updateCfg({
        provider: provider.value,
        model:    model.value.trim(),
        baseUrl:  baseUrl.value.trim(),
        apiKey:   keyVal,
      });
      const result = await AIConnector.testConnection();
      if (result.ok) {
        tip.textContent = `✓ 连接成功！模型: ${AIConnector.getModel()}`;
        tip.style.color = 'var(--c-done)';
        updateConfigStatus(true);
      } else {
        tip.textContent = `✗ 连接失败: ${result.error}`;
        tip.style.color = 'var(--c-danger)';
        updateConfigStatus(false);
      }
    });

    document.getElementById('btnCloseLLM')?.addEventListener('click', () => {
      document.getElementById('llmOutputCard').style.display = 'none';
    });
  }

  // 更新配置状态
  updateConfigStatus(AIConnector.isConfigured());

  // ── Skill 列表（全部12个，不只是MVP）
  const sl = document.getElementById('skillList');
  if (sl) {
    sl.innerHTML = '';
    TaskAPI.getTasks().sort((a,b)=>a.seq-b.seq).forEach(task => {
      const item = document.createElement('div');
      item.className = 'skill-item';
      item.innerHTML = `
        <span class="skill-name">${task.skill}</span>
        <span class="skill-type badge ${task.isMvp ? 'badge-mvp' : 'badge-stub'}">${task.isMvp ? 'MVP' : 'Stub'}</span>
        <button class="skill-trigger ${AIConnector.isConfigured() ? 'real' : ''}" data-id="${task.id}">
          ${AIConnector.isConfigured() ? '▶ 真实调用' : '▶ Mock'}
        </button>
      `;
      item.querySelector('button').addEventListener('click', () => {
        if (AIConnector.isConfigured()) {
          runRealSkill(task.id);
        } else {
          TaskAPI.triggerSkill(task.id);
          updateProgress(); renderBoard(); renderList(); renderSubtaskNav();
          toast(`✦ ${task.skill} (Mock)`, 'info');
        }
      });
      sl.appendChild(item);
    });
  }

  // ── API Docs
  const docs = document.getElementById('apiDocs');
  if (docs) {
    docs.innerHTML = [
      { m:'GET',  p:'/api/tasks',            d:'获取所有任务' },
      { m:'GET',  p:'/api/tasks/:id',         d:'获取单个任务' },
      { m:'PUT',  p:'/api/tasks/:id/status',  d:'更新任务状态' },
      { m:'POST', p:'/api/tasks/:id/trigger', d:'触发 Skill（真实LLM）' },
      { m:'GET',  p:'/api/stats',             d:'获取统计数据' },
      { m:'POST', p:'/api/signals/pause',     d:'发送 pause 信号' },
      { m:'POST', p:'/api/signals/resume',    d:'发送 resume 信号' },
      { m:'POST', p:'/api/signals/cancel',    d:'发送 cancel 信号' },
    ].map(e => `
      <div class="api-endpoint">
        <span class="api-method m-${e.m.toLowerCase()}">${e.m}</span>
        <span class="api-path">${e.p}</span>
        <span class="api-desc">${e.d}</span>
      </div>
    `).join('');
  }
}

function updateConfigStatus(connected) {
  const badge  = document.getElementById('modelBadge');
  const status = document.getElementById('configStatus');
  const modeBadge = document.getElementById('streamModeBadge');
  if (connected) {
    const m = AIConnector.getModel();
    if (badge)  { badge.textContent = m; badge.style.background = '#1f6feb22'; badge.style.color = '#58a6ff'; }
    if (status) { status.textContent = '已连接'; status.style.color = 'var(--c-done)'; }
    if (modeBadge) { modeBadge.textContent = 'Live · ' + m; modeBadge.style.background = '#1f8b4c22'; modeBadge.style.color = '#3fb950'; }
  } else {
    if (badge)  { badge.textContent = '未配置'; badge.style.background = ''; badge.style.color = ''; }
    if (status) { status.textContent = '未连接'; status.style.color = 'var(--text-3)'; }
    if (modeBadge) { modeBadge.textContent = 'Mock'; modeBadge.style.background = ''; modeBadge.style.color = ''; }
  }
}

// ── 真实 Skill 调用
async function runRealSkill(taskId) {
  const task = TaskAPI.getTask(taskId);
  if (!task) return;

  // 更新状态为 doing
  TaskAPI.updateStatus(taskId, 'doing');
  updateProgress(); renderBoard(); renderList(); renderSubtaskNav();
  toast(`▶ 真实调用: ${task.skill}`, 'info');

  // 显示输出面板
  const card   = document.getElementById('llmOutputCard');
  const output = document.getElementById('llmOutput');
  const label  = document.getElementById('llmTaskLabel');
  if (card)   card.style.display = 'block';
  if (output) output.textContent = '';
  if (label)  label.textContent  = `${task.id} · ${task.name} · ${AIConnector.getModel()}`;

  // 滚动到输出区
  card?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  let tokenCount = 0;

  await AIConnector.callStream(
    task,
    // onToken
    (token) => {
      if (output) output.textContent += token;
      tokenCount++;
      // 每10个token发一个事件
      if (tokenCount % 10 === 0) {
        AIBus.emit('tool.call', { agent: task.skill, tool: 'stream_token', count: tokenCount });
      }
    },
    // onDone
    (fullText) => {
      TaskAPI.updateStatus(taskId, 'done');
      task.events.push({ time: now(), text: `LLM输出 (${tokenCount} tokens): ${fullText.slice(0,60)}...` });
      updateProgress(); renderBoard(); renderList(); renderSubtaskNav();
      AIBus.emit('task.status', { id: taskId, name: task.name, from: 'doing', to: 'done', tokens: tokenCount });
      toast(`✓ ${task.skill} 执行完成 (${tokenCount} tokens)`, 'success', 4000);
    },
    // onError
    (errMsg) => {
      TaskAPI.updateStatus(taskId, 'backlog');
      updateProgress(); renderBoard(); renderList(); renderSubtaskNav();
      if (output) output.textContent += `\n\n[错误] ${errMsg}`;
      AIBus.emit('task.status', { id: taskId, error: errMsg });
      toast(`✗ ${task.skill} 调用失败: ${errMsg.slice(0,50)}`, 'error', 5000);
    }
  );
}

// ─────────────────────────────────────────────────────────────
// 10. EVENT STREAM & LOG
// ─────────────────────────────────────────────────────────────
function appendStreamLine(ev) {
  const el = document.getElementById('eventStream');
  if (!el) return;
  const topicClass = ev.topic.startsWith('task') ? 'task' : ev.topic.startsWith('tool') ? 'tool' : 'agent';
  const line = document.createElement('div');
  line.className = 'ev-line';
  line.innerHTML = `
    <span class="ev-time">${ev.timestamp.slice(11,23)}</span>
    <span class="ev-topic ${topicClass}">${ev.topic}</span>
    <span class="ev-payload">${JSON.stringify(ev.payload).slice(0,80)}</span>
  `;
  el.insertBefore(line, el.firstChild);
  if (el.children.length > 60) el.removeChild(el.lastChild);
}

function appendLogEntry(ev) {
  const el = document.getElementById('logBody');
  if (!el) return;
  const f = document.getElementById('logFilter')?.value || 'all';
  if (f !== 'all' && ev.topic !== f) return;
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  entry.innerHTML = `
    <span class="log-ts">${ev.timestamp.slice(11,23)}</span>
    <span class="log-topic">${ev.topic}</span>
    <span class="log-producer">${ev.producer}</span>
    <span class="log-payload">${JSON.stringify(ev.payload).slice(0,100)}</span>
  `;
  el.insertBefore(entry, el.firstChild);
  if (el.children.length > 200) el.removeChild(el.lastChild);
}

function rebuildLog() {
  const el = document.getElementById('logBody');
  if (!el) return;
  const f = document.getElementById('logFilter')?.value || 'all';
  el.innerHTML = '';
  AIBus.getLogs(f).forEach(ev => {
    const e = document.createElement('div');
    e.className = 'log-entry';
    e.innerHTML = `
      <span class="log-ts">${ev.timestamp.slice(11,23)}</span>
      <span class="log-topic">${ev.topic}</span>
      <span class="log-producer">${ev.producer}</span>
      <span class="log-payload">${JSON.stringify(ev.payload).slice(0,100)}</span>
    `;
    el.appendChild(e);
  });
}

// ─────────────────────────────────────────────────────────────
// 11. DRAWER
// ─────────────────────────────────────────────────────────────
function openDrawer(taskId) {
  const task = TaskAPI.getTask(taskId);
  if (!task) return;
  const leader = LEADERS.find(l => l.id === task.leader);

  document.getElementById('dId').textContent    = task.id;
  document.getElementById('dName').textContent  = task.name;
  document.getElementById('dLeader').textContent = leader ? `${leader.icon} ${leader.name}` : task.leader;
  document.getElementById('dSkill').textContent  = task.skill;
  document.getElementById('dMvp').innerHTML = task.isMvp
    ? '<span class="badge badge-mvp">MVP 完整实现</span>'
    : task.isStub ? '<span class="badge badge-stub">Stub 骨架</span>' : '—';

  const sel = document.getElementById('dStatus');
  sel.innerHTML = STATUS_OPTS.map(s =>
    `<option value="${s.value}" ${task.status === s.value ? 'selected' : ''}>${s.label}</option>`
  ).join('');
  sel.onchange = () => {
    TaskAPI.updateStatus(taskId, sel.value);
    updateProgress(); renderBoard(); renderList(); renderSubtaskNav();
    toast(`${task.name} → ${sel.options[sel.selectedIndex].text}`, 'info');
  };

  document.getElementById('dTools').innerHTML = task.tools.map(t => `<span class="tag">${t}</span>`).join('');
  document.getElementById('dRules').innerHTML = task.rules.map(r => `<div class="rule-item">${r}</div>`).join('');

  // 构建输出区：有结构化 output_data 时展示 JSON，否则展示 summary
  const outputHtml = (() => {
    const od = task.output_data;
    const styleMatch = task.skill === 'material_style' ? od?.style_match : null;
    const styleRouteHtml = styleMatch ? `
      <div style="margin-bottom:12px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg-1)">
        <div style="font-size:12px;font-weight:700;color:var(--text-1);margin-bottom:6px">风格决策</div>
        <div style="font-size:12px;color:var(--text-2);margin-bottom:4px">
          最终选择：<span style="color:var(--c-primary);font-weight:700">${styleMatch.selected_style_key || '—'}</span>
          ${styleMatch.confidence ? `<span style="margin-left:10px;color:var(--text-3)">置信度：${styleMatch.confidence}</span>` : ''}
        </div>
        ${(styleMatch.top_candidates || []).length ? `
          <div style="margin-top:6px">
            <div style="font-size:11px;font-weight:600;color:var(--text-3);margin-bottom:4px">候选排序</div>
            ${(styleMatch.top_candidates || []).map((candidate, idx) => `
              <div style="font-size:11px;color:var(--text-2);margin-bottom:3px">${idx + 1}. ${candidate.style_key}${candidate.score !== undefined ? ` (${candidate.score})` : ''}</div>
            `).join('')}
          </div>` : ''
        }
        ${(styleMatch.tone_tags || []).length ? `
          <div style="margin-top:8px">
            <div style="font-size:11px;font-weight:600;color:var(--text-3);margin-bottom:4px">Tone Tags</div>
            <div>${styleMatch.tone_tags.map(tag => `<span class="tag">${tag}</span>`).join('')}</div>
          </div>` : ''
        }
        ${(styleMatch.top_candidates?.[0]?.reasons || []).length ? `
          <div style="margin-top:8px">
            <div style="font-size:11px;font-weight:600;color:var(--text-3);margin-bottom:4px">判断依据</div>
            ${(styleMatch.top_candidates[0].reasons || []).slice(0, 5).map(reason => `
              <div style="font-size:11px;color:var(--text-2);margin-bottom:3px">- ${reason}</div>
            `).join('')}
          </div>` : ''
        }
      </div>
    ` : '';
    if (od && typeof od === 'object' && Object.keys(od).length > 0) {
      const rows = Object.entries(od).map(([k, v]) => {
        if (task.skill === 'material_style' && k === 'style_match') return '';
        let display = '';
        if (Array.isArray(v)) {
          display = v.length === 0
            ? '<span style="color:var(--text-3)">（空）</span>'
            : `<ul style="margin:2px 0 0 12px;padding:0;list-style:disc">${v.slice(0,6).map(item =>
                `<li style="font-size:11px;color:var(--text-2);margin-bottom:2px">${
                  typeof item === 'object' ? JSON.stringify(item, null, 0).slice(0, 120) : String(item).slice(0, 120)
                }</li>`
              ).join('')}${v.length > 6 ? `<li style="color:var(--text-3);font-size:11px">…共 ${v.length} 项</li>` : ''}</ul>`;
        } else if (typeof v === 'object' && v !== null) {
          display = `<pre style="font-size:11px;color:var(--text-2);white-space:pre-wrap;margin:2px 0 0 0;background:var(--bg-1);border-radius:4px;padding:4px 6px">${JSON.stringify(v, null, 2).slice(0, 400)}</pre>`;
        } else {
          display = `<span style="font-size:12px;color:var(--text-1)">${v === null || v === undefined ? '<span style="color:var(--text-3)">—</span>' : String(v).slice(0, 300)}</span>`;
        }
        return `<div style="margin-bottom:8px">
          <div style="font-size:11px;font-weight:600;color:var(--c-primary);margin-bottom:2px;text-transform:uppercase;letter-spacing:.03em">${k}</div>
          <div>${display}</div>
        </div>`;
      }).join('');
      return `<div style="font-size:12px;padding:4px 0">${styleRouteHtml}${rows}</div>`;
    }
    // 无结构化数据：降级展示 summary
    return `<span style="font-size:12px;color:var(--text-2)">${task.output || '暂无输出'}</span>`;
  })();

  document.getElementById('dIO').innerHTML = `
    <div class="io-item"><div class="io-label">Input</div><div class="io-value">${task.input}</div></div>
    <div class="io-item"><div class="io-label">Output</div><div class="io-value" style="max-height:340px;overflow-y:auto">${outputHtml}</div></div>
  `;

  const evEl = document.getElementById('dEvents');
  evEl.innerHTML = task.events.length === 0
    ? '<span style="font-size:12px;color:var(--text-3)">暂无事件</span>'
    : task.events.slice(-8).reverse().map(e => `
        <div class="event-item">
          <span class="event-time">${e.time.slice(11,19)}</span>
          <span class="event-text">${e.text}</span>
        </div>`).join('');

  document.getElementById('dTrigger').onclick = () => {
    TaskAPI.triggerSkill(taskId);
    updateProgress(); renderBoard(); renderList(); renderSubtaskNav();
    toast(`✦ Skill 触发: ${task.skill}`, 'success');
    closeDrawer();
  };

  // 绑定 drawer 内搜索（只绑一次，用 _drawerSearchBound 防重复）
  const dsInput = document.getElementById('drawerSearch');
  if (dsInput && !dsInput._bound) {
    dsInput._bound = true;
    let _dsTimer = null;
    dsInput.addEventListener('input', () => {
      clearTimeout(_dsTimer);
      _dsTimer = setTimeout(() => drawerHighlight(dsInput.value.trim()), 150);
    });
  }
  // 每次打开 drawer 都清空并重置
  if (dsInput) { dsInput.value = ''; }
  drawerHighlight('');
  const countEl = document.getElementById('drawerSearchCount');
  if (countEl) countEl.textContent = '';

  document.getElementById('overlay').classList.add('open');
  document.getElementById('drawer').classList.add('open');
}

function closeDrawer() {
  document.getElementById('overlay').classList.remove('open');
  document.getElementById('drawer').classList.remove('open');
  // 清空搜索框
  const ds = document.getElementById('drawerSearch');
  if (ds) ds.value = '';
  drawerHighlight('');
}

// ── Drawer 内容高亮搜索 ──────────────────────────────────────
function drawerHighlight(q) {
  const body = document.getElementById('drawer-body-content');
  if (!body) return;

  // 先还原所有高亮
  body.querySelectorAll('mark.drawer-hl').forEach(mark => {
    const parent = mark.parentNode;
    parent.replaceChild(document.createTextNode(mark.textContent), mark);
    parent.normalize();
  });

  const countEl = document.getElementById('drawerSearchCount');
  if (!q) { if (countEl) countEl.textContent = ''; return; }

  // 遍历文本节点高亮
  let count = 0;
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      // 跳过 input/script/style 内部
      const tag = node.parentElement?.tagName?.toLowerCase();
      if (['input','textarea','script','style'].includes(tag)) return NodeFilter.FILTER_REJECT;
      return node.textContent.toLowerCase().includes(q.toLowerCase())
        ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    }
  });

  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);

  nodes.forEach(node => {
    const text = node.textContent;
    const lc   = text.toLowerCase();
    const ql   = q.toLowerCase();
    const frag = document.createDocumentFragment();
    let last = 0;
    let idx  = lc.indexOf(ql);
    while (idx !== -1) {
      if (idx > last) frag.appendChild(document.createTextNode(text.slice(last, idx)));
      const mark = document.createElement('mark');
      mark.className = 'drawer-hl';
      mark.textContent = text.slice(idx, idx + q.length);
      frag.appendChild(mark);
      count++;
      last = idx + q.length;
      idx = lc.indexOf(ql, last);
    }
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    node.parentNode.replaceChild(frag, node);
  });

  // 滚动到第一个高亮
  const firstMark = body.querySelector('mark.drawer-hl');
  if (firstMark) firstMark.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  if (countEl) countEl.textContent = count > 0 ? `${count} 处` : '无匹配';
}

// ─────────────────────────────────────────────────────────────
// 12. PROGRESS & AGENT STATUS
// ─────────────────────────────────────────────────────────────
function updateProgress() {
  if (activeProjectId !== 'ai-design') return;
  const bar = document.getElementById('globalBar');
  const pct = document.getElementById('globalPct');
  if (boardSnapshotMode && currentBoard) {
    if (bar) bar.style.width = currentBoard.overall_progress + '%';
    if (pct) pct.textContent = currentBoard.overall_progress + '%';
    return;
  }
  const stats = TaskAPI.getStats();
  if (bar) bar.style.width = stats.pct + '%';
  if (pct) pct.textContent = stats.pct + '%';
}

function setAgent(state, label) {
  const dot = document.getElementById('agentDot');
  const txt = document.getElementById('agentText');
  if (dot) { dot.className = 'agent-dot' + (state === 'running' ? ' running' : state === 'done' ? ' done' : state === 'error' ? ' error' : ''); }
  if (txt) txt.textContent = label;
}

// ─────────────────────────────────────────────────────────────
// 13. TOAST
// ─────────────────────────────────────────────────────────────
function toast(msg, type = 'info', dur = 3000) {
  const c = document.getElementById('toasts');
  if (!c) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), dur);
}

// ─────────────────────────────────────────────────────────────
// 14. VIEW ROUTING
// ─────────────────────────────────────────────────────────────
function switchView(id) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`view-${id}`)?.classList.add('active');
  document.querySelector(`[data-view="${id}"]`)?.classList.add('active');

  if (id === 'timeline') renderTimeline();
  if (id === 'ai')       renderAIPanel();
  if (id === 'log')      rebuildLog();
  if (id === 'renders')  tryLoadRenders();
  if (id === 'discuss')  { /* 讨论区不需要重建，直接显示 */ }
}

// ─────────────────────────────────────────────────────────────
// 15. UTILS
// ─────────────────────────────────────────────────────────────
function now()      { return new Date().toISOString(); }
function sleep(ms)  { return new Promise(r => setTimeout(r, ms)); }

async function fetchBoardJson(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Failed to load ${url}`);
  return response.json();
}

function mapBoardStatusToTaskStatus(status) {
  const mapping = {
    pending: 'backlog',
    running: 'doing',
    waiting_input: 'blocked',
    waiting_confirm: 'review',
    blocked: 'blocked',
    done: 'done',
    error: 'blocked',
    cancelled: 'blocked',
  };
  return mapping[status] || 'backlog';
}

function boardLeaderForSkill(skill) {
  const task = TASKS_INIT.find(item => item.skill === skill);
  return task ? task.leader : 'research';
}

function mapBoardStageToTask(stage, index) {
  const template = TASKS_INIT.find(item => item.skill === stage.specialist);
  const task = template ? JSON.parse(JSON.stringify(template)) : {
    id: `SP-${String(index + 1).padStart(3, '0')}`,
    name: stage.phase,
    leader: boardLeaderForSkill(stage.specialist),
    seq: index + 1,
    isMvp: false,
    isStub: false,
    skill: stage.specialist,
    tools: [],
    rules: [],
    input: 'workflow context',
    output: stage.summary || 'stage output',
    status: 'backlog',
    events: [],
  };
  task.name = stage.phase;
  task.status = mapBoardStatusToTaskStatus(stage.status);
  task.output = stage.summary || task.output;
  task.output_data = stage.output || null;
  task.events = [
    {
      time: stage.updated_at || now(),
      text: stage.summary || `${stage.phase} 已更新`,
    },
  ];
  return task;
}

function mapBoardTimelineToBusLog(timeline, traceId) {
  return (timeline || []).map((item, index) => ({
    event_id: `board-${index}`,
    trace_id: traceId,
    timestamp: item.timestamp,
    topic: item.event.includes('project') ? 'task.status' : item.event.includes('started') ? 'skill.invoke' : 'agent.thought',
    event_type: item.event.replaceAll('.', '_'),
    producer: item.event.split('.')[0] || 'system',
    payload: { summary: item.summary },
  })).reverse();
}

function hydrateProjectsFromBoard(board, boardIndex) {
  const current = COMPANY_PROJECTS.find(project => project.id === 'ai-design');
  if (!current || !board) return;
  current.name = board.project_name || current.name;
  current.shortName = board.project_name || current.shortName;
  current.desc = `${board.brief_summary || ''} · ${board.stages?.length || 0} 阶段`;
  current.taskCount = board.stages?.length || 0;
  current.isActive = true;
  current.isCurrent = true;
  if (Array.isArray(boardIndex?.runs)) {
    boardIndex.runs.slice(0, 3).forEach((run, offset) => {
      const project = COMPANY_PROJECTS[offset + 1];
      if (!project) return;
      project.name = run.title;
      project.shortName = run.title.slice(0, 6);
      project.desc = `${run.current_phase} · ${run.overall_progress}%`;
      project.taskCount = board.stages?.length || project.taskCount;
    });
  }
}

async function loadBoardSnapshot(showToast = false) {
  try {
    const [board, boardIndex] = await Promise.all([
      fetchBoardJson(CURRENT_BOARD_URL),
      fetchBoardJson(BOARD_INDEX_URL).catch(() => ({ runs: [] })),
    ]);
    currentBoard = board;
    currentBoardIndex = boardIndex;
    boardSnapshotMode = true;
    TaskAPI.hydrate((board.stages || []).map(mapBoardStageToTask));
    AIBus.hydrate(
      mapBoardTimelineToBusLog(board.timeline || [], board.run_id),
      board.run_id,
      board.status === 'running' ? 'running' : 'idle'
    );
    hydrateProjectsFromBoard(board, boardIndex);
    setAgent(
      board.status === 'running' ? 'running' : board.status === 'done' ? 'done' : board.status === 'error' ? 'error' : 'idle',
      `${board.current_phase || '已同步'} · ${board.status || 'done'}`
    );
    renderProjectSelector();
    renderSubtaskNav();
    renderBoard();
    renderList();
    updateProgress();
    rebuildLog();
    if (document.getElementById('view-timeline')?.classList.contains('active')) renderTimeline();
    // 尝试加载效果图
    tryLoadRenders();
    if (showToast) toast(`已同步项目进度：${board.title}`, 'success');
  } catch (error) {
    boardSnapshotMode = false;
    if (showToast) toast('未找到当前工程的看板数据，请先运行 demo。', 'warn');
  }
}

// ─────────────────────────────────────────────────────────────
// 16-A. 效果图画廊模块
// ─────────────────────────────────────────────────────────────
let _selectedImageIdx = -1;
let _generatedImages  = [];
let _generatedSchemes = [];

async function tryLoadRenders() {
  try {
    // 从 API 拿最新 result，解析 generated_schemes / generated_images
    const board = await fetchBoardJson(`${API_BASE}/boards/current`);
    const result = board.result || {};

    if (result.generated_schemes && result.generated_schemes.length > 0) {
      _generatedSchemes = result.generated_schemes;
      // 兼容旧字段：取第一套方案的图片
      _generatedImages = result.generated_schemes.flatMap(s => s.images || []);
      renderSchemesGallery(_generatedSchemes);
    } else if (result.generated_images && result.generated_images.length > 0) {
      _generatedImages = result.generated_images;
      _generatedSchemes = [];
      renderImageGallery(_generatedImages);
    } else {
      const gallery = document.getElementById('imgGallery');
      if (gallery) gallery.innerHTML = '<div class="gallery-empty">暂无效果图，请先运行工作流生成</div>';
    }
  } catch (_) { /* 静默失败 */ }
}

function renderSchemesGallery(schemes) {
  const gallery = document.getElementById('imgGallery');
  if (!gallery) return;
  gallery.innerHTML = '';

  if (!schemes || schemes.length === 0) {
    gallery.innerHTML = '<div class="gallery-empty">暂无效果图，请先运行工作流生成</div>';
    return;
  }

  // 顶层包装，强制 block 流式布局，与外层 grid 隔离
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:block;width:100%;box-sizing:border-box;';
  gallery.appendChild(wrap);

  // ── Tab 栏 ──
  const tabBar = document.createElement('div');
  tabBar.style.cssText = 'display:flex;gap:8px;margin-bottom:16px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:2px;';
  wrap.appendChild(tabBar);

  // ── 各方案容器 ──
  const containers = [];

  schemes.forEach((scheme, sIdx) => {
    const isFirst = sIdx === 0;

    // Tab 按钮
    const tab = document.createElement('button');
    tab.dataset.schemeIdx = sIdx;
    tab.style.cssText = `padding:6px 14px;border-radius:6px;border:1px solid var(--border);background:${isFirst ? 'var(--c-primary)' : 'var(--bg-2)'};color:${isFirst ? '#fff' : 'var(--text-2)'};cursor:pointer;font-size:12px;font-weight:${isFirst ? '600' : '400'};white-space:nowrap;flex-shrink:0;transition:background .12s;`;
    tab.textContent = `方案${scheme.scheme_id || sIdx + 1}（${scheme.scheme_name || ''}）`;
    tabBar.appendChild(tab);

    // 方案内容区
    const container = document.createElement('div');
    container.dataset.schemeIdx = sIdx;
    container.style.cssText = `display:${isFirst ? 'block' : 'none'};width:100%;box-sizing:border-box;`;
    wrap.appendChild(container);
    containers.push(container);

    // 方案标题条
    const header = document.createElement('div');
    header.style.cssText = 'margin-bottom:14px;padding:10px 14px;background:var(--bg-2);border-radius:6px;border-left:3px solid var(--c-primary);';
    header.innerHTML = `
      <div style="font-size:13px;font-weight:600;color:var(--text-1)">方案${scheme.scheme_id}：${scheme.scheme_name || ''}</div>
      ${scheme.scheme_description ? `<div style="font-size:11px;color:var(--text-3);margin-top:4px">${scheme.scheme_description}</div>` : ''}
      ${scheme.style_variant ? `<div style="font-size:11px;color:var(--c-primary);margin-top:2px">风格：${scheme.style_variant}</div>` : ''}
    `;
    container.appendChild(header);

    // 图片网格（强制三列平铺）
    const grid = document.createElement('div');
    grid.style.cssText = 'display:grid;grid-template-columns:repeat(3,1fr);gap:16px;width:100%;box-sizing:border-box;';

    const images = scheme.images || [];
    images.forEach((img, iIdx) => {
      const globalIdx = schemes.slice(0, sIdx).reduce((acc, s) => acc + (s.images || []).length, 0) + iIdx;
      grid.appendChild(_makeImageCard(img, globalIdx));
    });

    if (images.length === 0) {
      grid.innerHTML = '<div class="gallery-empty">该方案暂无效果图</div>';
    }

    container.appendChild(grid);

    // Tab 点击切换（在局部 wrap 内操作，不用 document.querySelectorAll）
    tab.addEventListener('click', () => {
      tabBar.querySelectorAll('button').forEach((t, ti) => {
        const active = ti === sIdx;
        t.style.background = active ? 'var(--c-primary)' : 'var(--bg-2)';
        t.style.color      = active ? '#fff' : 'var(--text-2)';
        t.style.fontWeight = active ? '600' : '400';
      });
      containers.forEach((c, ci) => { c.style.display = ci === sIdx ? 'block' : 'none'; });
    });
  });

  const selInfo = document.getElementById('imgSelectionInfo');
  if (selInfo) {
    selInfo.textContent = _selectedImageIdx >= 0
      ? `已选定第 ${_selectedImageIdx + 1} 张 · ${_generatedImages[_selectedImageIdx]?.angle || ''}`
      : `共 ${schemes.length} 套方案 · ${_generatedImages.length} 张效果图`;
  }
}

function _makeImageCard(img, globalIdx) {
  const card = document.createElement('div');
  card.className = `img-card${_selectedImageIdx === globalIdx ? ' selected' : ''}`;
  card.innerHTML = `
    <div class="img-angle-label">${img.angle || `视角 ${globalIdx + 1}`}</div>
    ${img.url
      ? `<img src="${img.url}" alt="${img.angle}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" style="width:100%;border-radius:4px;display:block">
         <div class="img-placeholder" style="display:none"><div class="img-placeholder-icon">🖼</div><div>图片加载失败</div></div>`
      : `<div class="img-placeholder"><div class="img-placeholder-icon">🖼</div><div>${img.status === 'error' ? '生成失败' : '图片加载中'}</div>${img.error ? `<div class="img-error-msg" style="font-size:10px;color:var(--c-danger);margin-top:4px">${img.error}</div>` : ''}</div>`
    }
    <div class="img-prompt-preview" style="font-size:11px;color:var(--text-3);margin-top:6px;line-height:1.4">${(img.prompt || '').slice(0, 80)}...</div>
    <div class="img-card-actions" style="display:flex;gap:6px;margin-top:8px">
      <button class="img-btn-select ${_selectedImageIdx === globalIdx ? 'active' : ''}" data-idx="${globalIdx}" style="flex:1;padding:4px 8px;font-size:11px;border-radius:4px;border:1px solid var(--border);background:${_selectedImageIdx === globalIdx ? 'var(--c-done)' : 'var(--bg-2)'};color:${_selectedImageIdx === globalIdx ? '#fff' : 'var(--text-2)'};cursor:pointer;">
        ${_selectedImageIdx === globalIdx ? '✓ 已选定' : '选择此图'}
      </button>
      <button class="img-btn-prompt" data-idx="${globalIdx}" style="padding:4px 8px;font-size:11px;border-radius:4px;border:1px solid var(--border);background:var(--bg-2);color:var(--text-2);cursor:pointer;">查看 Prompt</button>
    </div>
  `;
  card.querySelector('.img-btn-select').addEventListener('click', e => {
    e.stopPropagation();
    selectImage(globalIdx);
  });
  card.querySelector('.img-btn-prompt').addEventListener('click', e => {
    e.stopPropagation();
    showPromptModal(img);
  });
  return card;
}

function renderImageGallery(images) {
  const gallery = document.getElementById('imgGallery');
  if (!gallery) return;
  gallery.innerHTML = '';

  if (!images || images.length === 0) {
    gallery.innerHTML = '<div class="gallery-empty">暂无效果图，请先运行工作流生成</div>';
    return;
  }

  const grid = document.createElement('div');
  grid.className = 'img-gallery-grid';

  images.forEach((img, idx) => {
    grid.appendChild(_makeImageCard(img, idx));
  });
  gallery.appendChild(grid);

  const selInfo = document.getElementById('imgSelectionInfo');
  if (selInfo) {
    selInfo.textContent = _selectedImageIdx >= 0
      ? `已选定第 ${_selectedImageIdx+1} 张 · ${images[_selectedImageIdx]?.angle || ''}`
      : '请选择一张效果图进行确认';
  }
}

function selectImage(idx) {
  _selectedImageIdx = idx;
  // scheme 模式下刷新 scheme 画廊保持 tab 布局；否则刷新 flat 画廊
  if (_generatedSchemes && _generatedSchemes.length > 0) {
    renderSchemesGallery(_generatedSchemes);
  } else {
    renderImageGallery(_generatedImages);
  }
  const img = _generatedImages[idx];
  toast(`已选定：${img?.angle || `视角 ${idx+1}`}`, 'success');
  AIBus.emit('task.status', { agent: 'visual_prompt', state: 'image_selected', idx, angle: img?.angle });
  appendDiscussionMsg('system', `[效果图确认] 用户选定：${img?.angle || `视角 ${idx+1}`} · Prompt: ${(img?.prompt || '').slice(0, 60)}...`);
}

function showPromptModal(img) {
  const modal = document.getElementById('promptModal');
  const content = document.getElementById('promptModalContent');
  if (!modal || !content) return;
  content.textContent = img.prompt || '(无 Prompt)';
  modal.style.display = 'flex';
}

// ─────────────────────────────────────────────────────────────
// 16-B. AI 讨论区（会议室模式）
// ─────────────────────────────────────────────────────────────
const _discussionLog = [];

function appendDiscussionMsg(role, text, meta = {}) {
  const entry = { role, text, time: now(), ...meta };
  _discussionLog.push(entry);
  renderDiscussionMsg(entry);
}

function renderDiscussionMsg(entry) {
  const el = document.getElementById('discussionLog');
  if (!el) return;
  const div = document.createElement('div');
  div.className = `disc-msg disc-msg-${entry.role}`;
  div.innerHTML = `
    <span class="disc-role">${entry.role === 'user' ? '👤 你' : entry.role === 'ai' ? '🤖 AI' : '⚙ 系统'}</span>
    <span class="disc-text">${entry.text}</span>
    <span class="disc-time">${entry.time.slice(11,19)}</span>
  `;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

async function sendDiscussionMessage(text) {
  if (!text.trim()) return;
  appendDiscussionMsg('user', text);

  // 调用 LLM 进行 AI 参与讨论
  if (!AIConnector.isConfigured()) {
    appendDiscussionMsg('ai', `[Mock回复] 收到您的反馈："${text.slice(0,40)}"。AI 建议：基于当前需求和选定效果图，可以继续进行材料深化和动线优化。`);
    return;
  }

  const ctx = _discussionLog.slice(-6).map(m => `${m.role}: ${m.text}`).join('\n');
  const systemP = `你是一个空间设计AI协作助手，正在参与展厅设计方案讨论。根据上下文，给出简洁、专业的设计建议或决策分析（200字以内）。`;
  const userP   = `讨论历史：\n${ctx}\n\n请回应最新消息。`;

  appendDiscussionMsg('ai', '...(思考中)...');
  const lastMsg = _discussionLog[_discussionLog.length - 1];

  await AIConnector.callStream(
    { skill: 'design_discuss', tools: [], rules: [] },
    (token) => { lastMsg.text = lastMsg.text === '...(思考中)...' ? token : lastMsg.text + token; },
    (full)  => {
      lastMsg.text = full;
      const el = document.getElementById('discussionLog');
      if (el) {
        const msgs = el.querySelectorAll('.disc-msg-ai');
        const last = msgs[msgs.length - 1];
        if (last) last.querySelector('.disc-text').textContent = full;
      }
      toast('AI 已回复', 'success', 2000);
    },
    (err)   => { lastMsg.text = `[错误] ${err}`; toast(`AI 讨论失败: ${err.slice(0,40)}`, 'error'); }
  );
}

function initDiscussionPanel() {
  const input  = document.getElementById('discInput');
  const sendBtn = document.getElementById('discSend');
  if (!sendBtn) return;

  sendBtn.addEventListener('click', () => {
    const v = input?.value?.trim();
    if (v) { sendDiscussionMessage(v); if (input) input.value = ''; }
  });
  input?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const v = input.value.trim();
      if (v) { sendDiscussionMessage(v); input.value = ''; }
    }
  });

  // 快捷决策按钮
  document.querySelectorAll('[data-discuss-quick]').forEach(btn => {
    btn.addEventListener('click', () => {
      sendDiscussionMessage(btn.dataset.discussQuick);
    });
  });
}

// ─────────────────────────────────────────────────────────────
// 16-C. 工程启动面板（POST /run 触发真实工作流）
// ─────────────────────────────────────────────────────────────
function initRunPanel() {
  const runBtn    = document.getElementById('btnRunReal');
  const briefInput = document.getElementById('realBrief');
  const providerSel = document.getElementById('realImgProvider');
  const statusEl  = document.getElementById('runStatus');

  if (!runBtn) return;

  runBtn.addEventListener('click', async () => {
    const brief = briefInput?.value?.trim() || '为某科技企业设计 800㎡ 展厅，风格偏科技感与未来感，要求沉浸式互动体验。';
    const provider = providerSel?.value || 'cogview';

    if (statusEl) statusEl.textContent = '启动中...';
    runBtn.disabled = true;

    try {
      const body = { brief, image_provider: provider };
      const resp = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (resp.status === 202) {
        if (statusEl) statusEl.textContent = `已启动 · ${data.brief?.slice(0, 30)}...`;
        toast('工作流已启动，请等待结果...', 'success');
        // 启动轮询
        startBoardPolling();
      } else if (resp.status === 409) {
        if (statusEl) statusEl.textContent = '当前有工作流正在运行，请等待';
        toast('工作流正在运行中', 'warn');
      } else {
        if (statusEl) statusEl.textContent = `错误: ${JSON.stringify(data)}`;
        toast(`启动失败: ${data.error || '未知错误'}`, 'error');
      }
    } catch (e) {
      if (statusEl) statusEl.textContent = `网络错误: ${e.message}`;
      toast(`无法连接 server.py (port 8765)，请先运行 python server.py`, 'error', 6000);
    } finally {
      runBtn.disabled = false;
    }
  });
}

// ─────────────────────────────────────────────────────────────
// 16-D. 看板轮询（每5秒更新一次）
// ─────────────────────────────────────────────────────────────
let _pollTimer = null;

function startBoardPolling(intervalMs = 5000) {
  stopBoardPolling();
  _pollTimer = setInterval(async () => {
    try {
      const status = await fetchBoardJson(`${API_BASE}/status`);
      if (status.running) {
        setAgent('running', '工作流运行中...');
      } else {
        await loadBoardSnapshot(false);
        if (!status.running) {
          stopBoardPolling();
          setAgent('done', '已完成');
          toast('工作流完成，看板已更新', 'success', 4000);
        }
      }
    } catch (_) { /* 服务未启动时静默 */ }
  }, intervalMs);
}

function stopBoardPolling() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

// ─────────────────────────────────────────────────────────────
// 16. INIT
// ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  TaskAPI.init();
  AIConnector.load();
  AIBus.newTrace();

  initProjectSelector();
  initDiscussionPanel();
  initRunPanel();
  renderSubtaskNav();
  renderBoard();
  renderList();
  updateProgress();

  // Nav
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', e => { e.preventDefault(); switchView(item.dataset.view); });
  });

  // Topbar
  document.getElementById('btnRunMVP')?.addEventListener('click', () =>
    AIBus.runMVP().then(() => { renderBoard(); renderList(); renderSubtaskNav(); })
  );
  document.getElementById('btnRunDemo')?.addEventListener('click', () =>
    AIBus.runDemo().then(() => { renderBoard(); renderList(); renderSubtaskNav(); })
  );
  document.getElementById('btnViewToggle')?.addEventListener('click', () => {
    const r = confirm('重置所有任务到初始状态？');
    if (r) { TaskAPI.reset(); renderBoard(); renderList(); renderSubtaskNav(); updateProgress(); toast('已重置', 'info'); }
  });

  // Search
  let searchTimer = null;
  document.getElementById('searchInput')?.addEventListener('input', e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const q = e.target.value.trim();
      renderBoard(q);
      renderList(q);
    }, 200);
  });

  // AI Panel
  document.getElementById('btnPause')?.addEventListener('click',  () => AIBus.pause());
  document.getElementById('btnResume')?.addEventListener('click', () => AIBus.resume());
  document.getElementById('btnCancel')?.addEventListener('click', () => AIBus.cancel());

  // Drawer
  document.getElementById('drawerClose')?.addEventListener('click', closeDrawer);
  document.getElementById('overlay')?.addEventListener('click', closeDrawer);

  // Log
  document.getElementById('logFilter')?.addEventListener('change', rebuildLog);
  document.getElementById('btnClearLog')?.addEventListener('click', () => {
    AIBus.clearLogs();
    document.getElementById('logBody').innerHTML = '';
    document.getElementById('eventStream').innerHTML = '';
    toast('日志已清空', 'info');
  });

  // Subscribe
  TaskAPI.on(ev => {
    if (['status_changed','skill_done','reset'].includes(ev)) updateProgress();
  });

  // Seed events
  AIBus.emit('task.status', { agent: 'orchestrator', state: 'Initialized', projects: COMPANY_PROJECTS.length });
  AIBus.emit('agent.thought', { agent: 'orchestrator', content: '看板就绪，等待触发' });
  AIBus.emit('tool.call', { agent: 'skill_registry', tool: 'list_skills', count: 12 });

  toast(`FlowBoard 已加载 · ${COMPANY_PROJECTS.length} 个项目 · AI设计工作流就绪`, 'success', 4000);
});
