/* Shared, dependency-free navigation between Licop2022's published websites. */
(function () {
  'use strict';
  const script = document.currentScript;
  const current = script && script.getAttribute('data-site-nav');
  const sites = [
    {id:'hajime-nihongo',name:'初见日语',detail:'日语课程与学习记录',url:'https://licop2022.github.io/hajime-nihongo/',color:'#225474'},
    {id:'llm-study',name:'科研学习工作台',detail:'LLM、论文与学习笔记',url:'https://licop2022.github.io/llm-study/',color:'#386b76'},
    {id:'lecture-radar',name:'讲座雷达',detail:'广工讲座与学生事务',url:'https://licop2022.github.io/lecture-radar/',color:'#1f5c53'}
  ];
  function mount() {
    if (document.getElementById('licop-site-links')) return;
    const host = document.createElement('div');
    host.id = 'licop-site-links';
    const root = host.attachShadow({mode:'open'});
    const active = sites.find(s => s.id === current);
    root.innerHTML = `<style>
      :host{all:initial;position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:1000;color-scheme:light;font:14px/1.5 "Microsoft YaHei","PingFang SC",system-ui,sans-serif;--accent:${active ? active.color : '#225474'};color:#233b4b}
      *{box-sizing:border-box}details{position:relative}summary{display:flex;align-items:center;justify-content:center;gap:9px;list-style:none;cursor:pointer;background:#fff;color:#284553;border:1px solid #d4e0e5;border-radius:24px;padding:11px 17px;box-shadow:0 3px 16px #102b4020;user-select:none;font-weight:600;min-height:44px}
      summary::-webkit-details-marker{display:none}summary:hover{border-color:var(--accent);color:var(--accent)}summary svg{width:17px;height:17px;flex-shrink:0}.chevron{transition:transform .15s}details[open] .chevron{transform:rotate(180deg)}
      nav{position:absolute;bottom:56px;right:0;background:#fff;border:1px solid #d9e3e8;border-radius:14px;width:min(300px,calc(100vw - 28px));padding:10px;box-shadow:0 12px 38px #102b4026;max-height:calc(100dvh - 110px);overflow:auto}
      .heading{font-size:13px;color:#69808c;font-weight:600;padding:8px 10px 11px;border-bottom:1px solid #edf1f3;margin-bottom:5px}
      a,.current{display:flex;align-items:center;gap:12px;padding:12px 10px;border-radius:8px;text-decoration:none;color:#254452;text-align:left;font:inherit}
      a:hover{background:#edf4f7;color:var(--accent)}.current{background:#f3f6f8}.dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}.copy{flex:1;min-width:0}.name{display:block;font-size:14px;font-weight:600}.detail{display:block;font-size:12px;color:#718591;margin-top:3px}.tag{font-size:11px;color:#6b818e;white-space:nowrap}.arrow{font-size:16px;color:#64808f}
      summary:focus-visible,a:focus-visible{outline:3px solid #c29b5e;outline-offset:3px}@media(max-width:580px){:host{right:12px;bottom:calc(12px + env(safe-area-inset-bottom,0px))}summary{padding:10px 14px}}@media(prefers-reduced-motion:reduce){.chevron{transition:none}}
    </style><details><summary aria-label="我的网站：展开站点切换"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>我的网站<svg class="chevron" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="m5 12 5-5 5 5"/></svg></summary><nav aria-label="我的网站"><div class="heading">切换网站</div>${sites.map(s => {
      const text = `<span class="dot" style="background:${s.color}"></span><span class="copy"><span class="name">${s.name}</span><span class="detail">${s.detail}</span></span>`;
      return s.id === current ? `<span class="current" aria-current="page">${text}<span class="tag">当前网站</span></span>` : `<a href="${s.url}" target="_blank" rel="noopener noreferrer" aria-label="${s.name}（在新标签页打开）">${text}<span class="arrow" aria-hidden="true">↗</span></a>`;
    }).join('')}</nav></details>`;
    document.body.append(host);
    const details = root.querySelector('details'), summary = root.querySelector('summary');
    root.addEventListener('keydown', e => {if (e.key === 'Escape' && details.open) {details.open = false;summary.focus();}});
    root.addEventListener('click', e => {if (e.target.closest('a')) details.open = false;});
    document.addEventListener('pointerdown', e => {if (details.open && !e.composedPath().includes(host)) details.open = false;});
  }
  if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount, {once:true});
})();
