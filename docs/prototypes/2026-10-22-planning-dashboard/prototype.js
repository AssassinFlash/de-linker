/* THROWAWAY UI PROTOTYPE. A: Journal workbench; B: canvas-first; C: guided.
   Existing route, synthetic in-memory project, no API or engineering integration.
   Rectangular packing constants below are illustrative, not engineering rules. */
(function () {
  'use strict';
  var q = new URLSearchParams(location.search);
  var state = {
    lang: ['zh','en','de'].includes(q.get('lang')) ? q.get('lang') : 'zh',
    variant: ['A','B','C'].includes(q.get('variant')) ? q.get('variant') : 'A',
    workspace: q.get('workspace') === 'roof' ? 'roof' : 'overview',
    width: 30, length: 18, orientation: 'ew', obstacle: true, disabled: [],
    country: 'FR', annual: 120000, goal: 'self', profile: false, candidate: 'storage',
    revision: 1, runs: [], activeRun: null, saved: null, draft: null,
    overlay: null, errors: {}, view: 'iso', undo: [], origin: 'direct',
    sourceFailed: false, chat: [], inquiry: null, progress: 0
  };
  var app = document.getElementById('app');
  var overlayRoot = document.getElementById('overlay-root');
  var opener = null;
  var toastTimer;
  function t(zh, en, de) { return state.lang === 'zh' ? zh : state.lang === 'de' ? de : en; }
  function esc(value) { return String(value).replace(/[&<>"']/g, function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
  function n(value, digits) { return Number(value).toLocaleString(state.lang === 'de' ? 'de-DE' : state.lang === 'zh' ? 'zh-CN' : 'en-GB', {maximumFractionDigits: digits === undefined ? 0 : digits}); }
  function countryName(code) { try { return new Intl.DisplayNames([state.lang === 'zh' ? 'zh-CN' : state.lang], {type:'region'}).of(code); } catch(e) { return code; } }
  function projectName() { return t('里昂仓库', 'Lyon warehouse', 'Lagerhalle Lyon'); }
  function icon(name) {
    var paths = {
      overview:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
      roof:'<path d="m3 11 9-7 9 7-9 7-9-7Z"/><path d="m3 15 9 7 9-7M8 8l9 7M7 14l9-7"/>',
      energy:'<path d="m13 2-9 12h7l-1 8 10-13h-7l1-7Z"/>',
      devices:'<rect x="4" y="3" width="16" height="18" rx="3"/><path d="M8 7h8M8 17h8m-4-7v3"/>',
      report:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
      check:'<path d="m5 12 4 4L19 6"/>',
      arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>',
      back:'<path d="M19 12H5m5-5-5 5 5 5"/>',
      down:'<path d="m6 9 6 6 6-6"/>',
      close:'<path d="m6 6 12 12M18 6 6 18"/>',
      save:'<path d="M5 3h12l4 4v14H3V3h2Z"/><path d="M7 3v6h9V3M7 21v-8h10v8"/>',
      play:'<path d="m9 5 11 7-11 7V5Z"/>',
      info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
      globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
      location:'<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/>',
      clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
      link:'<path d="m10 13 4-4m-6 6-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 3 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0"/>',
      user:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
      draft:'<path d="M7 4h13v17H4V7h3V4Z"/><path d="M8 10h8M8 14h8m-8 4h5"/>',
      chat:'<path d="M21 11a8 8 0 0 1-8 8H6l-4 3V11a9 9 0 0 1 19 0Z"/><path d="M7 10h10M7 14h7"/>',
      spark:'<path d="m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3Z"/>',
      undo:'<path d="M4 10h10a6 6 0 0 1 0 12M4 10l5-5m-5 5 5 5"/>',
      cube:'<path d="m12 3 9 5v9l-9 5-9-5V8l9-5Z"/><path d="m3 8 9 5 9-5M12 13v9M8 5l9 5"/>',
      plan:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M10 10v10"/>',
      plus:'<path d="M12 4v16M4 12h16"/>',
      minus:'<path d="M4 12h16"/>',
      shield:'<path d="m12 3 8 3v6c0 5-8 10-8 10S4 17 4 12V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
      sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
      file:'<path d="M8 12h8m-8 4h6M6 3h8l5 5v13H5V3h1Z"/><path d="M14 3v5h5"/>',
      download:'<path d="M12 3v12m-4-4 4 4 4-4M4 17v4h16v-4"/>',
      warning:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/>'
    };
    return '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">' + (paths[name] || paths.info) + '</svg>';
  }
  function btn(label, action, cls, symbol, extra) { return '<button class="button ' + (cls || '') + '" data-act="' + action + '" ' + (extra || '') + '>' + (symbol ? icon(symbol) : '') + label + '</button>'; }
  function pill(label, cls) { return '<span class="status-pill ' + (cls || '') + '"><i class="dot"></i>' + label + '</span>'; }
  function selected(value, current) { return value === current ? ' selected' : ''; }
  function model() {
    return {width:state.width,length:state.length,orientation:state.orientation,obstacle:state.obstacle,disabled:state.disabled.slice(),country:state.country,annual:state.annual,goal:state.goal,profile:state.profile,candidate:state.candidate};
  }
  function clone(x) { return JSON.parse(JSON.stringify(x)); }
  function positions(m) {
    // Example geometry only: 2.00 x 1.15 m panel, 1 m edge, 0.22/0.50 m gaps.
    // A centre aisle and an optional rooflight are illustrative obstacles.
    var cells = [], colCount = Math.min(26,Math.floor((m.width - 2 + .22) / 2.22));
    var rows = Math.min(18,Math.floor((m.length - 2 + .5) / 1.65));
    for (var row=0;row<rows;row++) for (var col=0;col<colCount;col++) {
      var x=1+col*2.22,y=1+row*1.65;
      if (col === Math.floor(colCount/2)) continue;
      if (m.obstacle && x+2>m.width*.70 && x<m.width*.89 && y+1.15>m.length*.28 && y<m.length*.51) continue;
      var id=col+'-'+row;
      cells.push({x:x,y:y,id:id,enabled:!m.disabled.includes(id)});
    }
    return cells;
  }
  function count(m) { return positions(m || model()).filter(function(c){return c.enabled;}).length; }
  function capacity(m) { return count(m || model()) * .46; }
  function currentRun() { return state.runs.find(function(r){return r.id === state.activeRun;}) || null; }
  function latestRun() { return state.runs[state.runs.length-1] || null; }
  function stale(run) { return !!run && run.revision !== state.revision; }
  function runLabel(run) { return run ? 'R' + run.id + ' · v' + run.revision : '—'; }
  function candidateName(candidate) { return candidate === 'storage' ? t('光伏 + 储能','PV + storage','PV + Speicher') : t('光伏系统','PV system','PV-Anlage'); }
  function navItems() {
    return [
      ['overview','overview',t('项目概览','Overview','Übersicht')],
      ['roof','roof',t('屋顶与排布','Roof & layout','Dach & Belegung')],
      ['energy','energy',t('用能与目标','Energy & goals','Verbrauch & Ziele')],
      ['devices','devices',t('设备与方案','System options','Systemvarianten')],
      ['report','report',t('报告与清单','Report & bill of materials','Bericht & Stückliste')]
    ];
  }
  function countryOptions() {
    var codes=['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IS','IE','IT','LV','LI','LT','LU','MT','NL','NO','PL','PT','RO','SK','SI','ES','SE','CH','GB','AL','BA','ME','MK','RS','MD','UA','XK'];
    codes.sort(function(a,b){return countryName(a).localeCompare(countryName(b),state.lang);});
    return codes.map(function(c){return '<option value="'+c+'"'+selected(c,state.country)+'>'+esc(countryName(c))+' ('+c+')</option>';}).join('');
  }
  function navMarkup(guided) {
    return navItems().map(function(item,index){
      return '<button class="nav-button '+(state.workspace===item[0]?'active':'')+'" data-workspace="'+item[0]+'" title="'+esc(item[2])+'"'+(state.workspace===item[0]?' aria-current="page"':'')+'>'+(guided?'<i class="guided-number">'+(index+1)+'</i>':icon(item[1]))+'<span>'+item[2]+'</span>'+(item[0]==='report'&&state.runs.length?'<span class="nav-status">'+state.runs.length+'</span>':'')+'</button>';
    }).join('');
  }
  function sourceLabel() {
    return state.origin==='home'?t('从首页屋顶入口进入','From the homepage roof entry','Über den Dach-Einstieg der Startseite'):state.origin==='product'?t('从产品页进入','From a product page','Über eine Produktseite'):t('示例项目 · 工商业','Demo project · Commercial','Beispielprojekt · Gewerbe');
  }
  function header() {
    return '<header class="site-header"><button class="brand" data-act="entries" aria-label="Linker"><img src="/assets/linker-logo.webp" alt="Linker"></button><nav class="site-links" aria-label="'+t('站点导航','Site navigation','Seitennavigation')+'"><button data-act="entries">'+t('首页','Home','Startseite')+'</button><button data-act="entries">'+t('产品','Products','Produkte')+'</button><button class="active" data-act="home-workspace">'+t('方案设计','Solution Configurator','Lösungskonfigurator')+'</button><button data-act="entries">'+t('应用方案','Applications','Anwendungen')+'</button><button data-act="entries">Journal</button></nav><div class="header-actions"><button class="site-language '+(state.lang==='en'?'current':'')+'" data-lang="en">EN</button><button class="site-language '+(state.lang==='de'?'current':'')+'" data-lang="de">DE</button><button class="icon-button" data-act="saved" aria-label="'+t('我的项目预览','My projects preview','Meine Projekte – Vorschau')+'">'+icon('user')+'</button><button class="icon-button" data-act="draft" aria-label="'+t('方案草稿预览','Solution draft preview','Lösungsentwurf – Vorschau')+'">'+icon('draft')+(state.draft?'<span class="count-dot">1</span>':'')+'</button><button class="contact-button" data-act="inquiry">'+t('联系团队','Contact us','Kontakt')+'</button></div></header>';
  }
  function reviewBar() {
    return '<div class="prototype-note"><div class="note-left"><span class="proto-badge">'+t('设计原型','DESIGN PROTOTYPE','DESIGNPROTOTYP')+'</span><span>'+t('可操作的界面示例 · 数据为演示 · 不产生真实询盘','Interactive design · Sample data · No real inquiries','Interaktiver Entwurf · Beispieldaten · Keine echten Anfragen')+'</span></div><div class="review-actions"><button data-act="entries">'+t('看站点入口','Site entries','Einstiege ansehen')+'</button><button data-act="state" class="state-button">'+t('查看状态','View state','Status ansehen')+'</button><select id="review-language" aria-label="'+t('预览语言','Preview language','Vorschausprache')+'"><option value="zh"'+selected('zh',state.lang)+'>中文</option><option value="en"'+selected('en',state.lang)+'>English</option><option value="de"'+selected('de',state.lang)+'>Deutsch</option></select></div></div>';
  }
  function sidebar() {
    return '<aside class="sidebar"><div class="sidebar-brand"><span class="mark">L</span><span>'+t('方案工作台','Project workspace','Projektbereich')+'</span></div><div class="sidebar-section">'+t('当前项目','Current project','Aktuelles Projekt')+'</div><nav class="workspace-nav" aria-label="'+t('项目工作区','Project workspaces','Projektbereiche')+'">'+navMarkup(false)+'</nav><div class="sidebar-bottom"><div class="sidebar-help"><button data-act="saved">'+icon('save')+'<span>'+t('已保存项目','Saved projects','Gespeicherte Projekte')+'</span></button><button data-act="sources">'+icon('shield')+'<span>'+t('依据与适用范围','Sources & scope','Quellen & Geltungsbereich')+'</span></button><button data-act="genie">'+icon('chat')+'<span>'+t('询问 Genie','Ask Genie','Genie fragen')+'</span></button></div></div></aside>';
  }
  function topbar() {
    return '<div class="project-topbar"><div><div class="breadcrumbs"><span>'+t('Solution Configurator','Solution Configurator','Lösungskonfigurator')+'</span><span>/</span><span>'+t('项目','Project','Projekt')+'</span></div><div class="project-title"><h1>'+projectName()+'</h1><button class="icon-button" data-act="project" aria-label="'+t('项目设置','Project settings','Projekteinstellungen')+'">'+icon('down')+'</button></div><div class="project-meta"><button data-act="project">'+icon('location')+esc(countryName(state.country))+'</button><i class="meta-divider"></i><span>'+sourceLabel()+'</span><i class="meta-divider"></i><span>'+t('输入版本','Input version','Eingabeversion')+' v'+state.revision+'</span></div></div><div class="project-actions">'+btn('<span class="save-label">'+t('保存项目','Save project','Projekt speichern')+'</span>','save','','save')+btn(t('生成报告预览','Create report preview','Berichtsvorschau erstellen'),'run','primary','play')+'</div></div>';
  }
  function staleBanner(run) {
    if (!stale(run)) return '';
    return '<div class="stale-banner">'+icon('clock')+'<p>'+t('输入已修改。当前报告仍是','Inputs changed. This report still shows','Eingaben geändert. Dieser Bericht zeigt weiterhin')+' '+runLabel(run)+' · '+t('更新后再带入询盘。','Update it before using it in an inquiry.','Aktualisieren Sie ihn vor der Übernahme in eine Anfrage.')+'</p>'+btn(t('更新预览','Update preview','Vorschau aktualisieren'),'run','small')+'</div>';
  }
  function metrics(m, ready) {
    return '<div class="metric-grid">'+metric(t('屋顶排布','Roof layout','Dachbelegung'),n(count(m)),'',t('块参考组件 · 可逐块调整','reference modules · editable','Referenzmodule · anpassbar'),'roof')+metric(t('光伏装机功率（DC）','PV capacity (DC)','PV-Leistung (DC)'),n(capacity(m),2),'kWp',t('数量 × 演示组件 460 Wp','Count × example module 460 Wp','Anzahl × Beispielmodul 460 Wp'),'energy')+metric(t('预计年发电量','Annual generation','Jahresertrag'),'—','',t('待接入气象数据与仿真','Weather data and simulation required','Wetterdaten und Simulation erforderlich'),'sun')+metric(t('设计状态','Design status','Planungsstatus'),ready?t('示例结果','Demo result','Beispiel'):t('草案','Draft','Entwurf'),'',t('电气、结构及当地要求待核验','Electrical, structural and local checks pending','Elektrische, statische und lokale Prüfung offen'),'shield')+'</div>';
  }
  function metric(label,value,unit,note,symbol) { return '<div class="metric"><div class="metric-label">'+icon(symbol)+label+'</div><div class="metric-value">'+value+(unit?'<small>'+unit+'</small>':'')+'</div><div class="metric-note">'+note+'</div></div>'; }
  function roofSvg(m, editable, topView) {
    var cells=positions(m), prefix='s'+Math.random().toString(36).slice(2,7);
    function pt(x,y,z) {
      if(topView) return [95+x/m.width*510,80+y/m.length*275-(z||0)];
      return [83+x/m.width*363+y/m.length*171,182-x/m.width*91+y/m.length*163-(z||0)];
    }
    function ps(points) { return points.map(function(v){return pt(v[0],v[1],v[2]).map(function(k){return k.toFixed(1);}).join(',');}).join(' '); }
    function rect(x,y,w,h,z) {return ps([[x,y,z],[x+w,y,z],[x+w,y+h,z],[x,y+h,z]]);}
    var W=m.width,L=m.length;
    var s='<svg viewBox="0 0 700 440" xmlns="http://www.w3.org/2000/svg" role="group" aria-label="'+t('示例工业屋顶排布图','Illustrative commercial roof layout','Beispielhafte Dachbelegung einer Gewerbehalle')+'"><title>'+t('示例屋顶；非测绘或工程设计结果','Illustrative roof; no survey or engineering result','Beispieldach; kein Aufmaß oder technischer Plan')+'</title><defs><linearGradient id="'+prefix+'roof" x2="0.7" y2="1"><stop stop-color="#d4ded3"/><stop offset="1" stop-color="#bac8b9"/></linearGradient><linearGradient id="'+prefix+'wall"><stop stop-color="#aebdaf"/><stop offset="1" stop-color="#e1e8dd"/></linearGradient><filter id="'+prefix+'shadow" x="-30%" y="-50%" width="180%" height="220%"><feGaussianBlur stdDeviation="11"/></filter></defs>';
    s+='<ellipse cx="360" cy="351" rx="254" ry="35" fill="#7b8f7a" opacity=".12" filter="url(#'+prefix+'shadow)"/>';
    if(!topView) {
      s+='<polygon points="'+ps([[0,L,0],[W,L,0],[W,L,-32],[0,L,-32]])+'" fill="url(#'+prefix+'wall)"/><polygon points="'+ps([[W,0,0],[W,L,0],[W,L,-32],[W,0,-32]])+'" fill="#b0c0ad"/>';
      for(var wall=1;wall<12;wall++){var x=W*wall/12;s+='<path d="M'+pt(x,L,-4).join(' ')+'L'+pt(x,L,-28).join(' ')+'" stroke="#90a58f" stroke-width=".7" opacity=".4"/>';}
      s+='<polygon points="'+ps([[W*.73,L,-3],[W*.89,L,-3],[W*.89,L,-30],[W*.73,L,-30]])+'" fill="#79927f" opacity=".55"/>';
    }
    s+='<polygon points="'+rect(0,0,W,L,0)+'" fill="url(#'+prefix+'roof)" stroke="#a1b59f" stroke-width="1.2"/>';
    for(var stripe=1;stripe<25;stripe++){var sy=L*stripe/25;s+='<path d="M'+pt(0,sy).join(' ')+'L'+pt(W,sy).join(' ')+'" stroke="#8ea38d" stroke-width=".55" opacity=".24"/>';}
    s+='<polygon points="'+rect(.55,.55,W-1.1,L-1.1,0)+'" fill="none" stroke="#f2f5ef" stroke-width="1" stroke-dasharray="4 4" opacity=".7"/>';
    cells.forEach(function(c){
      var title=(c.enabled?t('移除第','Exclude module ','Modul ausschließen: '):t('恢复第','Restore module ','Modul wiederherstellen: '))+c.id+(state.lang==='zh'?'块组件':'');
      if(!editable)title=t('参考组件 ','Reference module ','Referenzmodul ')+c.id;
      s+='<g class="solar-cell" '+(editable?'data-panel="'+c.id+'" tabindex="0" role="button" aria-pressed="'+c.enabled+'" aria-label="'+esc(title)+'"':'')+'><title>'+esc(title)+'</title><polygon points="'+rect(c.x,c.y,2,1.15,1)+'" fill="'+(c.enabled?'#344f64':'#d7e1d2')+'" stroke="'+(c.enabled?'#698294':'#819b80')+'" stroke-width=".65"'+(!c.enabled?' stroke-dasharray="2 2"':'')+'/>';
      if(c.enabled) {
        s+='<path d="M'+pt(c.x+1,c.y,1).join(' ')+'L'+pt(c.x+1,c.y+1.15,1).join(' ')+'" stroke="#8ea9b9" stroke-width=".45" opacity=".65"/>';
        for(var line=1;line<3;line++)s+='<path d="M'+pt(c.x,c.y+1.15*line/3,1).join(' ')+'L'+pt(c.x+2,c.y+1.15*line/3,1).join(' ')+'" stroke="#a0b3bb" stroke-width=".35" opacity=".42"/>';
        if(m.orientation==='ew')s+='<path d="M'+pt(c.x,c.y,1).join(' ')+'L'+pt(c.x+2,c.y,1).join(' ')+'" stroke="#b9cbd2" stroke-width=".9" opacity=".7"/>';
      }
      s+='</g>';
    });
    if(m.obstacle) {
      s+='<polygon points="'+rect(W*.71,L*.30,W*.16,L*.18,5)+'" fill="#b2c1b2" stroke="#839b86" stroke-width="1"/><polygon points="'+rect(W*.73,L*.315,W*.12,L*.14,6)+'" fill="#dce6db" stroke="#b0c2ae" stroke-width=".6"/>';
      for(var sl=1;sl<4;sl++)s+='<path d="M'+pt(W*(.73+.12*sl/4),L*.315,6).join(' ')+'L'+pt(W*(.73+.12*sl/4),L*.455,6).join(' ')+'" stroke="#a8bda8" stroke-width="1"/>';
    }
    s+='<g fill="#69826e" font-family="Jakarta,sans-serif" font-size="9"><path d="M630 91V58m-5 8 5-9 5 9" stroke="#69826e" fill="none" stroke-width="1.2"/><text x="626" y="49">N</text><path d="M80 381h72m-72-3v6m72-6v6" stroke="#849987" fill="none"/><text x="80" y="399">'+t('示意比例','Illustrative scale','Schematischer Maßstab')+'</text></g></svg>';
    return s;
  }
  function nextStep(symbol,title,copy,workspace) {return '<div class="next-step"><span class="step-dot '+(workspace?'active':'')+'">'+icon(symbol)+'</span><div><strong>'+title+'</strong><p>'+copy+'</p>'+(workspace?'<button class="text-link" data-workspace="'+workspace+'">'+t('继续','Continue','Weiter')+icon('arrow')+'</button>':'')+'</div></div>';}
  function overview() {
    var m=model(), run=latestRun();
    return '<div class="section-header"><div><div class="section-label">'+t('当前项目','CURRENT PROJECT','AKTUELLES PROJEKT')+'</div><h2>'+t('把现场条件变成可沟通的方案','Turn site details into a system proposal','Ein Anlagenentwurf auf Basis Ihrer Standortdaten')+'</h2><p>'+t('从屋顶开始，也可以先配置设备。所有工作区共用这个项目。','Start with the roof or explore system options. Every workspace belongs to this project.','Beginnen Sie beim Dach oder bei den Systemvarianten. Alle Bereiche gehören zu diesem Projekt.')+'</p></div></div>'+metrics(m,!!run)+
      '<div class="overview-grid"><div class="overview-main"><div class="preview-panel"><div class="preview-top"><span class="glass">'+icon('roof')+t('工商业 · 平屋顶','Commercial · Flat roof','Gewerbe · Flachdach')+'</span><span class="glass">'+t('示例排布','Illustrative layout','Beispielbelegung')+'</span></div><div class="preview-visual">'+roofSvg(m,false,false)+'</div><div class="preview-caption"><div><h3>'+t('看看这个屋顶可以如何布置','Explore a layout for this roof','Eine Belegung für dieses Dach erkunden')+'</h3><p>'+n(state.width)+' × '+n(state.length)+' m · '+t('天窗与通道已示意保留','Rooflight and aisle shown','Lichtkuppel und Gang dargestellt')+'</p></div>'+btn(t('打开屋顶工作区','Open roof workspace','Dachbereich öffnen'),'open-roof','primary','arrow')+'</div></div></div><aside class="overview-rail"><h3>'+t('接下来做什么','Your next steps','Ihre nächsten Schritte')+'</h3>'+
      nextStep('roof',t('确认屋顶条件','Confirm roof details','Dachdaten prüfen'),t('检查尺寸、障碍物和可用区域。','Check dimensions, obstacles and usable areas.','Maße, Hindernisse und nutzbare Flächen prüfen.'),'roof')+
      nextStep('energy',t('补充用能目标','Add energy goals','Verbrauchsziele ergänzen'),t('此原型暂未演示已有光伏和纯储能的输入。','Existing-PV and storage-only inputs are not shown in this preview.','Eingaben für bestehende PV-Anlagen und reine Speicherprojekte sind in dieser Vorschau noch nicht dargestellt.'),'energy')+
      nextStep('devices',t('形成可讨论的方案','Explore system options','Systemvarianten ansehen'),t('查看方案差异、待核验项与物料清单。','Review options, open checks and materials.','Varianten, offene Prüfungen und Stückliste ansehen.'),'devices')+
      '<div class="rail-note">'+icon('info')+'<div>'+t('你将得到：屋顶示意、方案选项、可追溯的报告草案。工程放行前的缺项会保留在报告中。','You will get a roof illustration, system options and a traceable draft report. Outstanding checks stay visible.','Sie erhalten eine Dachskizze, Systemvarianten und einen nachvollziehbaren Berichtsentwurf. Offene Prüfungen bleiben sichtbar.')+'</div></div></aside></div>'+
      '<div class="lower-grid"><section class="panel panel-padding"><div class="card-heading"><h3>'+t('项目检查','Project checks','Projektprüfungen')+'</h3>'+pill(t('待核验','Checks pending','Prüfung offen'),'pending')+'</div>'+checkRow('roof',t('屋顶尺寸与组件数量','Roof dimensions and module count','Dachmaße und Modulanzahl'),t('可编辑示例','Editable example','Anpassbares Beispiel'))+checkRow('sun',t('当地气象与发电仿真','Local weather and yield simulation','Lokales Wetter und Ertragssimulation'),t('尚未计算','Not calculated','Nicht berechnet'))+checkRow('shield',t('电气、结构与当地要求','Electrical, structural and local requirements','Elektrische, statische und lokale Anforderungen'),t('需补充依据','Evidence required','Nachweise erforderlich'))+'<button class="text-link" data-act="sources">'+t('查看依据与缺项','View sources and open checks','Quellen und offene Prüfungen')+icon('arrow')+'</button></section><section class="panel panel-padding"><div class="card-heading"><h3>'+t('接到实际项目沟通','Continue the project conversation','Das Projekt weiter besprechen')+'</h3>'+icon('link')+'</div><p class="secondary-copy">'+t('此处预览设备方案、报告与询盘如何关联同一项目版本，以及交接时保留哪些已知条件和待核验项。','Preview how system options, reports and an inquiry can reference the same project version, including defined inputs and open checks.','Die Vorschau zeigt, wie Systemvarianten, Bericht und Anfrage auf dieselbe Projektversion verweisen und festgelegte Angaben sowie offene Prüfungen enthalten.')+'</p><div class="soft-card">'+icon('draft')+'<span><strong>'+t('Solution draft · 方案草稿','Solution draft','Lösungsentwurf')+'</strong>'+t('保留组件、设备及待确认项','Modules, equipment and open items retained','Module, Geräte und offene Punkte bleiben enthalten')+'</span></div><button class="text-link" data-act="draft">'+t('预览交接内容','Preview the handoff','Übergabe ansehen')+icon('arrow')+'</button></section></div>';
  }
  function checkRow(symbol,text,right) {return '<div class="check-row">'+icon(symbol)+'<span>'+text+'</span><span class="right">'+right+'</span></div>';}
  function roofWorkspace() {
    var error=state.errors.roof;
    return '<div class="section-header"><div><h2>'+t('屋顶与排布','Roof & layout','Dach & Belegung')+'</h2><p>'+t('调整尺寸，点击组件保留或排除。当前输入与假设在这个工作区内查看。','Adjust dimensions; click modules to include or exclude them. View current inputs and assumptions in this workspace.','Maße anpassen und Module durch Anklicken ein- oder ausschließen. Die aktuellen Eingaben und Annahmen finden Sie in diesem Bereich.')+'</p></div><button class="text-link" data-act="sources">'+t('排布依据','Layout assumptions','Belegungsannahmen')+icon('info')+'</button></div><div class="work-grid"><div><div class="roof-stage"><div class="canvas-top"><span class="glass">'+icon('roof')+t('屋顶 01 · 平屋顶示例','Roof 01 · Flat roof example','Dach 01 · Flachdachbeispiel')+'</span><span class="glass">'+t('示意图','Illustration','Schema')+'</span></div>'+roofSvg(model(),true,state.view==='plan')+'<div class="canvas-bottom"><div class="canvas-tools"><button data-act="iso" class="'+(state.view==='iso'?'active':'')+'" aria-label="'+t('立体视图','Isometric view','Räumliche Ansicht')+'">'+icon('cube')+'</button><button data-act="plan" class="'+(state.view==='plan'?'active':'')+'" aria-label="'+t('平面视图','Plan view','Draufsicht')+'">'+icon('plan')+'</button><button data-act="undo" '+(!state.undo.length?'disabled':'')+' aria-label="'+t('撤销屋顶修改','Undo roof edit','Dachänderung rückgängig')+'">'+icon('undo')+'</button></div><div class="canvas-legend"><span><i class="legend-square"></i>'+t('参考组件','Reference module','Referenzmodul')+'</span><span><i class="legend-square obstacle"></i>'+t('天窗','Rooflight','Lichtkuppel')+'</span></div></div></div><div class="roof-summary"><div><strong>'+n(count())+'</strong><small>'+t('块组件 · 点击可调整','modules · click to edit','Module · per Klick anpassen')+'</small></div><div><strong>'+n(capacity(),2)+' <span class="small-text">kWp</span></strong><small>'+t('数量 × 460 Wp（演示）','Count × 460 Wp (example)','Anzahl × 460 Wp (Beispiel)')+'</small></div><div><strong>'+n(state.width*state.length,2)+' <span class="small-text">m²</span></strong><small>'+t('屋顶投影面积','Roof plan area','Projizierte Dachfläche')+'</small></div></div><div class="wide-note"><div><strong>'+t('尺寸从哪里来？','Where do dimensions come from?','Woher stammen die Maße?')+'</strong><p>'+t('这里使用手工尺寸。地图描绘、测绘文件和多屋面编辑属于后续实现范围。','This preview uses manual dimensions. Map tracing, survey imports and multiple roof faces are implementation scope.','Diese Vorschau nutzt manuelle Maße. Kartenzeichnung, Aufmaßimporte und mehrere Dachflächen sind für die Umsetzung vorgesehen.')+'</p></div>'+btn(t('继续补充用能','Continue to energy','Weiter zum Verbrauch'),'open-energy','small','arrow')+'</div></div><aside class="inspector"><section><h3>'+t('屋顶条件','Roof details','Dachdaten')+'</h3><p class="sub">'+t('参考矩形平屋顶 · 手工输入','Reference rectangular flat roof · Manual input','Rechteckiges Beispielflachdach · Manuelle Eingabe')+'</p>'+(error?'<div class="field-error" role="alert">'+esc(error)+'</div>':'')+'<div class="field-grid">'+unitField('roof-width',t('长度','Length','Länge'),state.errors.rawWidth||state.width,'m')+unitField('roof-length',t('宽度','Width','Breite'),state.errors.rawLength||state.length,'m')+'</div>'+btn(t('应用尺寸','Apply dimensions','Maße übernehmen'),'apply-roof','full')+'<p class="field-hint">'+t('此界面示例支持 8–60 m × 6–32 m，可用逗号或点输入小数。','This interface example accepts 8–60 m × 6–32 m, with comma or point decimals.','Dieses Oberflächenbeispiel erlaubt 8–60 m × 6–32 m, mit Komma oder Punkt als Dezimalzeichen.')+'</p></section><section><h3>'+t('排布方向','Layout orientation','Belegungsrichtung')+'</h3><div class="segmented"><button data-orientation="ew" class="'+(state.orientation==='ew'?'active':'')+'">'+t('东西向示意','East–west example','Ost–West-Beispiel')+'</button><button data-orientation="south" class="'+(state.orientation==='south'?'active':'')+'">'+t('南向示意','South-facing example','Süd-Beispiel')+'</button></div><p class="field-hint">'+t('仅切换示意，不计算倾角、行间遮挡或风荷载。','Illustration only; tilt, row shading and wind loads are not calculated.','Nur Darstellung; Neigung, Reihenverschattung und Windlasten werden nicht berechnet.')+'</p></section><section><h3>'+t('屋顶障碍物','Roof obstacles','Dachhindernisse')+'</h3><div class="check-item"><span>'+t('天窗示例','Example rooflight','Beispiel-Lichtkuppel')+'</span>'+btn(state.obstacle?t('移除','Remove','Entfernen'):t('添加','Add','Hinzufügen'),'obstacle','small',state.obstacle?'minus':'plus')+'</div><div class="check-item"><span>'+t('检修通道','Access aisle','Wartungsgang')+'</span><span>'+t('示意保留','Shown','Dargestellt')+'</span></div></section><section><h3>'+t('当前依据','Current assumptions','Aktuelle Annahmen')+'</h3><p class="field-hint">'+t('2.00 × 1.15 m 参考组件、1 m 示意边距及通道。不代表当地规范或安装商布置规则。','2.00 × 1.15 m reference module, 1 m illustrative edge gap and an aisle. These are not local code or installer layout rules.','Referenzmodul 2,00 × 1,15 m, beispielhafter Randabstand 1 m und ein Gang. Dies sind keine lokalen Vorschriften oder Verlegeregeln.')+'</p><button class="text-link" data-act="sources">'+t('查看全部假设','View all assumptions','Alle Annahmen ansehen')+icon('arrow')+'</button></section></aside></div>';
  }
  function unitField(id,label,value,unit) {return '<label class="field" for="'+id+'"><span>'+label+'</span><div class="input-unit"><input id="'+id+'" inputmode="decimal" value="'+esc(value)+'"><b>'+unit+'</b></div></label>';}
  function energyWorkspace() {
    return '<div class="section-header"><div><h2>'+t('用能与目标','Energy & goals','Verbrauch & Ziele')+'</h2><p>'+t('国家用于项目条件；界面语言独立选择。可先提供年用电量，再补充负荷曲线。','The country sets project context; language is selected separately. Begin with annual consumption, then add a load profile.','Das Land bestimmt den Projektkontext; die Sprache wählen Sie separat. Beginnen Sie mit dem Jahresverbrauch und ergänzen Sie ein Lastprofil.')+'</p></div></div><div class="form-layout"><section class="panel panel-padding"><h3>'+t('这个项目希望实现什么？','What should this project achieve?','Was soll dieses Projekt erreichen?')+'</h3><div class="goal-grid">'+goalCard('self','sun',t('提高自用','Increase self-consumption','Eigenverbrauch erhöhen'),t('评估光伏与储能的配合','Explore PV and storage together','PV und Speicher gemeinsam betrachten'))+goalCard('peak','energy',t('降低需量峰值','Reduce demand peaks','Lastspitzen senken'),t('需要功率随时间的数据','Requires time-series power data','Benötigt zeitaufgelöste Leistungsdaten'))+goalCard('backup','shield',t('备用供电','Backup supply','Ersatzstrom'),t('关键负载与供电时长待补充','Critical loads and duration required','Kritische Lasten und Überbrückungszeit erforderlich'))+'</div><h3>'+t('负荷曲线','Load profile','Lastprofil')+'</h3><p class="field-hint">'+(state.profile?t('已加载合成的 24 小时曲线，用于预览图表。未运行储能或年度仿真。','A synthetic 24-hour curve is loaded to preview the chart. No storage or annual simulation has run.','Ein synthetisches 24-Stunden-Profil zeigt die Diagrammansicht. Keine Speicher- oder Jahressimulation wurde ausgeführt.'):t('现在只有年用电量；它不足以计算储能收益、自给率或削峰效果。','Annual consumption alone cannot establish storage performance, self-sufficiency or peak reduction.','Der Jahresverbrauch allein reicht nicht für Speicherwirkung, Autarkiegrad oder Lastspitzenreduktion.'))+'</p>'+loadChart()+'<div class="upload-box"><div><h4>'+t('先体验曲线导入后的样子','Preview a loaded profile','Ansicht mit Lastprofil ausprobieren')+'</h4><p>'+t('使用合成示例，不读取你的文件。真实导入需校验时间、单位和缺失值。','Uses a synthetic example without reading files. Real imports need timestamp, unit and missing-value validation.','Nutzt ein synthetisches Beispiel ohne Dateien einzulesen. Echte Importe erfordern Zeit-, Einheiten- und Lückenprüfung.')+'</p></div>'+btn(state.profile?t('移除示例','Remove example','Beispiel entfernen'):t('载入示例曲线','Load example profile','Beispielprofil laden'),'profile','small','file')+'</div></section><aside class="inspector"><section><h3>'+t('项目所在地','Project location','Projektstandort')+'</h3><p class="sub">'+t('示例建筑：里昂，法国','Sample building: Lyon, France','Beispielgebäude: Lyon, Frankreich')+'</p><label class="field" for="project-country"><span>'+t('项目国家','Project country','Projektland')+'</span><select id="project-country">'+countryOptions()+'</select></label>'+unitField('annual-consumption',t('年用电量','Annual consumption','Jahresverbrauch'),(state.errors.rawAnnual===undefined?state.annual:state.errors.rawAnnual),'kWh/'+t('年','year','Jahr'))+(state.errors.energy?'<div class="field-error">'+esc(state.errors.energy)+'</div>':'')+btn(t('应用项目数据','Apply project details','Projektdaten übernehmen'),'apply-energy','full')+'</section><section><h3>'+t('当地覆盖情况','Local coverage','Lokale Abdeckung')+'</h3>'+pill(t('待接入并核验','Integration and verification pending','Anbindung und Prüfung offen'),'pending')+'<p class="field-hint">'+t('此处可选择欧洲项目国家，用于检查界面与数据流。尚未接入任何国家的气象、并网或电价规则。','European countries are selectable to explore the interface and data flow. Weather, grid and tariff rules are not integrated for any country.','Europäische Länder sind zur Prüfung von Oberfläche und Datenfluss auswählbar. Wetter-, Netz- und Tarifregeln sind für kein Land angebunden.')+'</p><button class="text-link" data-act="sources">'+t('查看范围与缺项','View scope and open items','Umfang und offene Punkte')+icon('arrow')+'</button></section><section>'+btn(t('继续看设备方案','Explore system options','Systemvarianten ansehen'),'open-devices','full primary','arrow')+'</section></aside></div>';
  }
  function goalCard(id,symbol,title,copy) {return '<button class="goal-card '+(state.goal===id?'active':'')+'" data-goal="'+id+'" aria-pressed="'+(state.goal===id)+'">'+icon(symbol)+'<strong>'+title+'</strong><small>'+copy+'</small></button>';}
  function loadChart() {
    var values=[.35,.29,.26,.25,.27,.3,.42,.68,.84,.9,.96,.88,.82,.9,1,.92,.8,.62,.5,.46,.43,.4,.38,.36];
    var s='<svg class="chart" viewBox="0 0 600 180" role="img" aria-label="'+t('合成负荷曲线示例','Synthetic load-profile example','Synthetisches Beispiel-Lastprofil')+'">';
    for(var i=0;i<4;i++)s+='<path class="chart-grid" d="M30 '+(20+i*38)+'H580"/>';
    [0,6,12,18,23].forEach(function(h){s+='<text class="chart-label" x="'+(30+h*23.5)+'" y="173">'+String(h).padStart(2,'0')+':00</text>';});
    if(state.profile) {
      var path=values.map(function(v,j){return (j?'L':'M')+(30+j*23.5)+','+(145-v*113);}).join(' ');
      s+='<path d="'+path+'L570,150H30Z" fill="#d8ebe0" opacity=".7"/><path d="'+path+'" fill="none" stroke="#4f9478" stroke-width="2.2"/><text class="chart-label" x="33" y="13">'+t('相对负荷 · 合成示例','Relative load · synthetic example','Relative Last · synthetisches Beispiel')+'</text>';
    } else s+='<text x="300" y="91" text-anchor="middle" class="chart-label">'+t('载入示例后显示曲线','Load the example to see the profile','Beispiel laden, um das Profil zu sehen')+'</text>';
    return s+'</svg>';
  }
  function devicesWorkspace() {
    return '<div class="section-header"><div><h2>'+t('设备与方案','System options','Systemvarianten')+'</h2><p>'+t('比较方案组成。这里的设备仅示意角色，型号与适配性仍需真实数据和规则核验。','Compare system composition. Devices illustrate roles; models and compatibility require verified data and rules.','Vergleichen Sie den Systemaufbau. Geräte zeigen nur Rollen; Modelle und Kompatibilität erfordern geprüfte Daten und Regeln.')+'</p></div><button class="text-link" data-act="sources">'+t('选型依据','Selection evidence','Auswahlgrundlagen')+icon('info')+'</button></div><div class="device-grid">'+deviceCard('pv',t('方案 A','Option A','Variante A'),t('先规划光伏系统','Plan the PV system','PV-Anlage planen'),t('光伏组件与并网逆变器','PV modules and grid-connected inverter','PV-Module und netzgekoppelter Wechselrichter'))+deviceCard('storage',t('方案 B','Option B','Variante B'),t('将储能纳入项目','Include storage in the project','Speicher in das Projekt aufnehmen'),t('光伏、逆变器及储能系统','PV, inverter and storage system','PV, Wechselrichter und Speichersystem'))+'</div><div class="lower-grid"><section class="panel panel-padding"><h3>'+t('选型还需要哪些依据？','What evidence is still needed?','Welche Grundlagen fehlen noch?')+'</h3><ul class="check-list"><li>'+icon('clock')+t('组串、电压电流、MPPT 与温度边界核验','String, voltage, current, MPPT and temperature-limit checks','Prüfung von Strings, Spannung, Strom, MPPT und Temperaturgrenzen')+'</li><li>'+icon('clock')+t('负荷时序、储能功率容量、SOC 与控制策略','Time-series loads, storage power and capacity, SOC and dispatch','Lastzeitreihen, Speicherleistung und -kapazität, SOC und Betriebsstrategie')+'</li><li>'+icon('clock')+t('厂商兼容文件、当地并网与结构审核','Manufacturer compatibility documents, local grid and structural review','Hersteller-Kompatibilitätsunterlagen, lokale Netz- und Statikprüfung')+'</li></ul><button class="text-link" data-act="sources">'+t('查看来源与实现边界','View sources and implementation scope','Quellen und Umsetzungsumfang')+icon('arrow')+'</button></section><section class="panel panel-padding"><h3>'+t('当前方案组成','Current system composition','Aktueller Systemaufbau')+'</h3>'+bomTable(model(),true)+'<p class="field-hint">'+t('组件保留在工程清单中；当前站点没有组件产品分类。未确认项不会被包装成已经适配的产品。','Modules remain in the engineering list; the site has no module product category. Unresolved items are not presented as compatible products.','Module bleiben in der technischen Stückliste; die Website hat keine Produktkategorie für Module. Offene Positionen gelten nicht als kompatibel freigegebene Produkte.')+'</p>'+btn(t('生成报告预览','Create report preview','Berichtsvorschau erstellen'),'run','full primary','report')+'</section></div>';
  }
  function deviceCard(id,label,title,copy) {
    var active=state.candidate===id;
    return '<section class="device-card '+(active?'selected':'')+'"><div class="card-heading"><span class="section-label">'+label+'</span>'+(active?pill(t('当前草案','Current draft','Aktueller Entwurf'),'ready'):pill(t('可比较','Alternative','Alternative')) )+'</div><h3>'+title+'</h3><p class="field-hint">'+copy+'</p><div class="device-art" aria-hidden="true"><div class="inverter"></div>'+(id==='storage'?'<div class="battery"></div>':'')+'</div><div class="device-facts"><div><span>'+t('光伏','PV','PV')+'</span><strong>'+n(capacity(),2)+' kWp</strong></div><div><span>'+t('逆变器型号','Inverter model','Wechselrichtermodell')+'</span><strong>'+t('待选型','To be selected','Offen')+'</strong></div>'+(id==='storage'?'<div><span>'+t('储能容量','Storage capacity','Speicherkapazität')+'</span><strong>'+t('待计算','To be sized','Zu berechnen')+'</strong></div>':'')+'</div>'+btn(active?t('已选为草案','Selected as draft','Als Entwurf gewählt'):t('选择此方案','Choose this option','Variante wählen'),'candidate-'+id,active?'full':'full primary',active?'check':null)+'</section>';
  }
  function bomTable(m,compact) {
    var rows=[
      [t('参考光伏组件','Reference PV module','PV-Referenzmodul'),t('460 Wp · 仅用于示意','460 Wp · illustrative only','460 Wp · nur zur Darstellung'),n(count(m))],
      [t('逆变器','Inverter','Wechselrichter'),t('型号及电气匹配待核验','Model and electrical matching pending','Modell und elektrische Auslegung offen'),t('待选型','Open','Offen')]
    ];
    if(m.candidate==='storage') rows.push([t('储能系统','Storage system','Speichersystem'),t('功率、容量和厂商适配待核验','Power, capacity and manufacturer compatibility pending','Leistung, Kapazität und Herstellerkompatibilität offen'),t('待计算','Open','Offen')]);
    if(!compact)rows.push([t('支架、保护与电缆','Mounting system, protection and cables','Montagesystem, Schutzgeräte und Leitungen'),t('需项目工程设计补齐','Project engineering required','Projektbezogene Auslegung erforderlich'),t('待确认','Open','Offen')]);
    return '<table class="bom-table"><thead><tr><th>'+t('物料 / 工程范围','Material / engineering scope','Material / Planungsumfang')+'</th><th>'+t('数量 / 状态','Quantity / status','Anzahl / Status')+'</th></tr></thead><tbody>'+rows.map(function(r){return '<tr><td>'+r[0]+'<small>'+r[1]+'</small></td><td>'+r[2]+'</td></tr>';}).join('')+'</tbody></table>';
  }
  function reportWorkspace() {
    var run=currentRun();
    if(!run)return '<div class="section-header"><div><h2>'+t('报告与清单','Report & bill of materials','Bericht & Stückliste')+'</h2><p>'+t('报告会保留它所对应的项目输入与待核验项。','The report retains its project inputs and open checks.','Der Bericht enthält die zugehörigen Projekteingaben und offenen Prüfungen.')+'</p></div></div><div class="empty-state">'+icon('report')+'<h3>'+t('先生成一份示例报告','Create an example report','Beispielbericht erstellen')+'</h3><p>'+t('你会看到排布、方案组成、依据和缺项如何呈现。这里不会运行真实工程计算。','See how layout, system composition, assumptions and open checks are presented. This does not run engineering calculations.','Sehen Sie, wie Belegung, Systemaufbau, Annahmen und offene Prüfungen erscheinen. Es werden keine technischen Berechnungen ausgeführt.')+'</p>'+btn(t('生成报告预览','Create report preview','Berichtsvorschau erstellen'),'run','primary','report')+'</div>';
    return '<div class="section-header"><div><h2>'+t('报告与清单','Report & bill of materials','Bericht & Stückliste')+'</h2><p>'+t('每份报告都对应一个保留的输入版本。切换旧版本，内容也随之切换。','Each report belongs to a retained input version. Earlier versions retain their own contents.','Jeder Bericht gehört zu einer gespeicherten Eingabeversion. Frühere Versionen behalten ihre eigenen Inhalte.')+'</p></div>'+btn(t('导出示例 HTML','Export example HTML','Beispiel als HTML exportieren'),'export','small','download')+'</div><div class="history-list">'+state.runs.map(function(r){return '<button data-run="'+r.id+'" class="'+(r.id===state.activeRun?'active':'')+'">'+runLabel(r)+'</button>';}).join('')+'</div>'+staleBanner(run)+reportPaper(run)+'<div class="wide-note"><div><strong>'+t('带着这个版本继续沟通','Continue with this version','Mit dieser Version weiterarbeiten')+'</strong><p>'+t('草稿会保留组件、待选设备及未核验说明。示例不会提交真实询盘。','The draft retains modules, open equipment and unverified items. This preview submits no real inquiry.','Der Entwurf enthält Module, offene Gerätepositionen und Prüfhinweise. Die Vorschau versendet keine echte Anfrage.')+'</p></div>'+btn(stale(run)?t('更新后带入草稿','Update before adding','Vor Übernahme aktualisieren'):t('带入 Solution draft','Add to Solution draft','In Lösungsentwurf übernehmen'),'handoff','primary','draft')+'</div>';
  }
  function reportPaper(run) {
    var m=run.input;
    return '<article class="paper" id="report-paper"><div class="paper-header"><div><div class="paper-label">'+t('方案报告 · 示例','System report · example','Systembericht · Beispiel')+'</div><h2>'+projectName()+'</h2><p class="small-text">'+esc(countryName(m.country))+' · '+candidateName(m.candidate)+' · '+runLabel(run)+'</p></div><img src="/assets/linker-logo.webp" alt="Linker"></div><div class="paper-note">'+t('设计原型：此报告用于展示内容与版本关联。容量只按示例组件数量计算；尚无发电、储能、电气、结构或国家规则的计算与放行。','Design prototype: this report demonstrates content and version links. Capacity uses example module count only; generation, storage, electrical, structural and country-rule calculations and release are not implemented.','Designprototyp: Dieser Bericht zeigt Inhalte und Versionsbezüge. Die Leistung basiert nur auf der Beispiel-Modulanzahl. Ertrags-, Speicher-, Elektro-, Statik- und Länderprüfungen sowie Freigaben sind nicht umgesetzt.')+'</div><div class="paper-roof">'+roofSvg(m,false,false)+'</div><div class="data-row"><span>'+t('屋顶尺寸 / 组件数量','Roof dimensions / module count','Dachmaße / Modulanzahl')+'</span><strong>'+n(m.width)+' × '+n(m.length)+' m / '+n(count(m))+'</strong></div><div class="data-row"><span>'+t('光伏装机功率（DC）','PV capacity (DC)','PV-Leistung (DC)')+'</span><strong>'+n(count(m))+' × 460 Wp = '+n(capacity(m),2)+' kWp</strong></div><div class="data-row"><span>'+t('年发电量 / 自给率 / 自用比例','Annual yield / self-sufficiency / self-consumption','Jahresertrag / Autarkiegrad / Eigenverbrauchsanteil')+'</span><strong>'+t('尚未计算','Not calculated','Nicht berechnet')+'</strong></div><div class="paper-section">'+t('物料清单与工程范围','Bill of materials and engineering scope','Stückliste und Planungsumfang')+'</div>'+bomTable(m,false)+'<div class="paper-section">'+t('依据与待核验项','Assumptions and open checks','Annahmen und offene Prüfungen')+'</div><p class="secondary-copy">'+t('屋顶：手工矩形尺寸及示意障碍物。排布：固定参考组件、边距与通道。国家：仅作为项目数据。待补齐：现场测量、荷载与结构、组串与设备兼容、逐时负荷及气象、当地并网与电价规则。','Roof: manual rectangle dimensions and illustrative obstacles. Layout: fixed reference module, edge gaps and aisle. Country: project data only. Outstanding: survey, loads and structure, strings and device compatibility, time-series load and weather, local grid and tariff rules.','Dach: manuelle Rechteckmaße und Beispielhindernisse. Belegung: festes Referenzmodul, Randabstände und Gang. Das Land ist nur als Projekteingabe erfasst. Offen: Aufmaß, Lasten und Statik, Strings und Gerätekompatibilität, zeitaufgelöste Last- und Wetterdaten sowie lokale Netz- und Tarifregeln.')+'</p><button class="text-link" data-act="sources">'+t('查看来源说明','View source notes','Quellenhinweise ansehen')+icon('arrow')+'</button></article>';
  }
  function guidedIntro() {
    var tips={
      overview:[t('从你的项目开始','Start with your project','Mit Ihrem Projekt beginnen'),t('先了解要准备什么，再进入屋顶或用能工作区。','See what you need, then open the roof or energy workspace.','Sehen Sie, welche Angaben nötig sind, und öffnen Sie Dach oder Verbrauch.')],
      roof:[t('第一步，确认可用屋顶','First, confirm the usable roof','Zuerst die nutzbare Dachfläche prüfen'),t('输入尺寸、保留障碍物，再调整参考组件。','Enter dimensions, retain obstacles, then adjust reference modules.','Maße eingeben, Hindernisse berücksichtigen und Referenzmodule anpassen.')],
      energy:[t('接下来，说明用能需求','Next, describe your energy needs','Als Nächstes den Bedarf beschreiben'),t('选择项目国家、用电量及目标。负荷数据可稍后补充。','Choose country, consumption and goals. A load profile can follow later.','Land, Verbrauch und Ziele wählen. Ein Lastprofil kann später folgen.')],
      devices:[t('比较方案，保留未确认项','Compare options and retain open items','Varianten vergleichen und offene Punkte festhalten'),t('先判断方案方向；产品适配与工程计算需后续核验。','Choose a direction; device compatibility and engineering still need verification.','Eine Richtung wählen; Gerätekompatibilität und Auslegung sind noch zu prüfen.')],
      report:[t('检查报告，再交给团队','Review the report, then share with the team','Bericht prüfen und an das Team übergeben'),t('查看每项数字对应的输入、假设和缺项。','Check the inputs, assumptions and missing evidence behind each figure.','Eingaben, Annahmen und fehlende Nachweise zu den Werten ansehen.')]
    };
    return '<div class="guided-intro"><strong>'+tips[state.workspace][0]+'</strong><p>'+tips[state.workspace][1]+'</p></div>';
  }
  function switcher() {
    var name=state.variant==='A'?t('Journal 工作台','Journal workbench','Journal-Projektbereich'):state.variant==='B'?t('画布优先','Canvas first','Zeichenfläche im Fokus'):t('分步引导','Guided steps','Geführte Schritte');
    return '<div class="prototype-switcher" aria-label="'+t('切换设计方案','Switch design variant','Entwurfsvariante wechseln')+'"><button data-act="prev-variant" aria-label="'+t('上一种布局','Previous layout','Vorheriges Layout')+'">'+icon('back')+'</button><div class="variant-copy"><strong>'+state.variant+' · '+name+'</strong><small>'+t('同一项目 · 用 ← → 比较布局','Same project · Compare with ← →','Gleiches Projekt · Mit ← → vergleichen')+'</small></div><button data-act="next-variant" aria-label="'+t('下一种布局','Next layout','Nächstes Layout')+'">'+icon('arrow')+'</button><div class="variant-keys">'+['A','B','C'].map(function(v){return '<button data-variant="'+v+'" class="'+(v===state.variant?'current':'')+'" aria-label="'+t('布局','Layout','Layout')+' '+v+'">'+v+'</button>';}).join('')+'</div></div>';
  }
  function render() {
    document.documentElement.lang=state.lang==='zh'?'zh-CN':state.lang;
    document.title='Linker · '+t('方案工作台原型','Project workspace prototype','Prototyp Projektbereich');
    document.body.className=state.variant==='B'?'canvas-first':state.variant==='C'?'guided':'';
    var contents={overview:overview,roof:roofWorkspace,energy:energyWorkspace,devices:devicesWorkspace,report:reportWorkspace};
    app.innerHTML=header()+reviewBar()+'<div class="app-shell">'+sidebar()+'<main class="main">'+topbar()+(state.variant==='C'?'<nav class="guided-steps" aria-label="'+t('设计步骤','Design steps','Planungsschritte')+'">'+navMarkup(true)+'</nav>'+guidedIntro():'<nav class="mobile-workspaces" aria-label="'+t('项目工作区','Project workspaces','Projektbereiche')+'">'+navMarkup(false)+'</nav>')+(state.workspace!=='report'?staleBanner(latestRun()):'')+contents[state.workspace]()+'<div class="review-state" aria-label="'+t('原型状态','Prototype state','Prototypstatus')+'"><span>'+t('预览状态','Preview state','Vorschaustatus')+'</span><span>v'+state.revision+'</span><span>'+t('最近报告','Latest report','Letzter Bericht')+' '+runLabel(latestRun())+'</span><span>'+t('草稿','Draft','Entwurf')+' '+(state.draft?runLabel(state.draft):'—')+'</span><span>'+t('保存：仅本次预览','Save: preview session only','Speicherung: nur diese Vorschau')+'</span></div></main></div>'+switcher()+'<button class="floating-genie" data-act="genie" aria-label="'+t('询问 Genie','Ask Genie','Genie fragen')+'">'+icon('spark')+'</button>';
    renderOverlay();
    var horizontalNav=app.querySelector(state.variant==='C'?'.guided-steps':'.mobile-workspaces');
    var activeNav=horizontalNav&&horizontalNav.querySelector('.active');
    if(activeNav&&horizontalNav.clientWidth<horizontalNav.scrollWidth)horizontalNav.scrollLeft=activeNav.offsetLeft-horizontalNav.offsetLeft-8;
  }
  function dialog(title,subtitle,body,actions,cls) {
    return '<div class="overlay-backdrop" data-backdrop="true"><section class="dialog '+(cls||'')+'" role="dialog" aria-modal="true" aria-labelledby="dialog-title" tabindex="-1"><div class="dialog-head"><div><h2 id="dialog-title">'+title+'</h2>'+(subtitle?'<p>'+subtitle+'</p>':'')+'</div><button class="close" data-act="close" aria-label="'+t('关闭','Close','Schließen')+'">'+icon('close')+'</button></div><div class="dialog-body">'+body+'</div>'+(actions?'<div class="dialog-actions">'+actions+'</div>':'')+'</section></div>';
  }
  function renderOverlay() {
    var html='', run=currentRun()||latestRun(), m=run?run.input:model();
    if(state.overlay==='entries') {
      html=dialog(t('从站点不同入口，进入同一个项目','Different site entries, one project','Verschiedene Einstiege, ein Projekt'),t('站点联动预览 · 下方卡片仅示意导流位置','Site handoff preview · Cards illustrate entry placement','Vorschau der Website-Verknüpfung · Karten zeigen mögliche Einstiege'),
        '<div class="reference-note">'+t('首页、导航、相关内容和产品页都能进入方案工作台。这里仅展示入口与上下文如何衔接；不是已经改好的线上页面。','Homepage, navigation, related content and products can lead to the workspace. This previews entries and context, not implemented live pages.','Startseite, Navigation, passende Inhalte und Produkte führen in den Projektbereich. Dies zeigt Einstiege und Kontext, keine umgesetzten Live-Seiten.')+'</div><div class="entry-grid"><article class="entry-card"><div class="section-label">'+t('首页 / 导航 / 相关内容','HOMEPAGE / NAVIGATION / CONTENT','STARTSEITE / NAVIGATION / INHALTE')+'</div><div class="entry-art">'+roofSvg(model(),false,false)+'</div><h3>'+t('从你的屋顶开始设计','Start planning with your roof','Mit Ihrem Dach planen')+'</h3><p>'+t('工具作为站点重点能力，可直接打开屋顶工作区，并在项目中继续用能、设备和报告。','Give the tool a prominent site entry. Open the roof workspace directly, then continue to energy, devices and reports in the same project.','Das Werkzeug erhält einen sichtbaren Einstieg. Direkt den Dachbereich öffnen und im selben Projekt mit Verbrauch, Geräten und Bericht fortfahren.')+'</p>'+btn(t('预览首页进入','Try the homepage entry','Startseiten-Einstieg testen'),'entry-home','primary','arrow')+'</article><article class="entry-card"><div class="section-label">'+t('产品页 / 已有系统','PRODUCT PAGE / EXISTING SYSTEM','PRODUKTSEITE / BESTEHENDE ANLAGE')+'</div><div class="entry-art device-art"><div class="inverter"></div><div class="battery"></div></div><h3>'+t('把设备放进项目里考虑','Consider equipment within a project','Geräte im Projektkontext betrachten')+'</h3><p>'+t('此处模拟从产品页进入同一项目；当前没有导入产品型号或已有系统数据。','This simulates a product-page entry into the same project. No product model or existing-system data is imported.','Hier wird der Einstieg von einer Produktseite in dasselbe Projekt gezeigt. Produktmodelle und Daten einer bestehenden Anlage werden nicht übernommen.')+'</p>'+btn(t('预览产品页进入','Try the product entry','Produkt-Einstieg testen'),'entry-product','','arrow')+'</article></div>',btn(t('返回当前项目','Return to project','Zurück zum Projekt'),'close'), 'wide');
    } else if(state.overlay==='sources') {
      html=dialog(t('依据、计算与适用范围','Sources, calculations & scope','Quellen, Berechnungen & Geltungsbereich'),t('本原型已经做了什么，仍缺什么','What this prototype does and what remains open','Was der Prototyp zeigt und was noch fehlt'),
        '<div class="reference-note">'+t('这里展示未来“依据可查”的界面结构。演示数值没有采用任何工程标准，也不构成项目设计结果。','This shows the future source-inspection interface. Demonstration values do not apply engineering standards and are not project design results.','Hier sehen Sie die künftige Ansicht zur Quellenprüfung. Beispielwerte wenden keine technischen Normen an und sind keine Projektauslegung.')+'</div>'+
        sourceSection(t('已执行的示例算术','Example arithmetic performed','Ausgeführte Beispielrechnung'),t('矩形尺寸 → 固定网格排布 → 排除示意通道、天窗和手工移除的组件。直流装机功率 = 保留组件数量 × 460 Wp ÷ 1,000。','Rectangle dimensions → fixed grid → exclude illustrative aisle, rooflight and manually removed modules. PV DC capacity = retained module count × 460 Wp ÷ 1,000.','Rechteckmaße → festes Raster → Beispielgang, Lichtkuppel und manuell entfernte Module aussparen. DC-Leistung = verbleibende Modulanzahl × 460 Wp ÷ 1.000.'))+
        sourceSection(t('演示输入与假设','Demonstration inputs and assumptions','Beispieleingaben und Annahmen'),t('2.00 × 1.15 m 参考组件；1 m 示例边距；0.22 m / 0.50 m 网格间隙；中央示意通道。都是原型常量，无标准依据。转向不改变几何间距或能量结果。','2.00 × 1.15 m reference module; 1 m example edge gap; 0.22 m / 0.50 m grid gaps; illustrative central aisle. These are prototype constants without a standards basis. Orientation changes do not alter spacing or energy results.','Referenzmodul 2,00 × 1,15 m; beispielhafter Randabstand 1 m; Rasterabstände 0,22 m / 0,50 m; schematischer Mittelgang. Dies sind Prototypkonstanten ohne Normgrundlage. Die Ausrichtung ändert weder Abstände noch Energieergebnisse.'))+
        sourceSection(t('未实现的工程判断','Engineering judgements not implemented','Nicht umgesetzte technische Prüfungen'),t('屋顶测量与倾角、行间遮挡、逐时气象与发电、负荷和 SOC、逆变器与电池选型、组串校验、风雪荷载、结构与消防、并网要求。未确认的结果保持空白。','Roof survey and tilt, row shading, hourly weather and yield, loads and SOC, inverter and battery sizing, string checks, wind/snow loads, structure/fire protection and grid requirements. Unverified results remain empty.','Aufmaß und Dachneigung, Reihenverschattung, stündliche Wetter- und Ertragsdaten, Lasten und SOC, Wechselrichter- und Speicherauslegung, Stringprüfung, Wind-/Schneelasten, Statik/Brandschutz und Netzanforderungen. Ungeprüfte Ergebnisse bleiben leer.'))+
        sourceSection(t('全欧洲适用不等于全部已支持','Europe-wide scope does not establish coverage','Europaweiter Umfang bedeutet noch keine Abdeckung'),t('国家选择用于演示项目数据流。各国规则、适用标准、数据版本与审核日期需逐项建立。商业平屋顶、支架与结构边界须由真实输入及专业审核支持。','Country selection demonstrates project data flow. National rules, applicable standards, dataset versions and review dates must be established individually. Commercial flat-roof, mounting and structural boundaries require real inputs and professional review.','Die Länderauswahl zeigt den Projektdatenfluss. Nationale Regeln, anwendbare Normen, Datenversionen und Prüfdaten sind einzeln aufzubauen. Gewerbliche Flachdach-, Montage- und Statikgrenzen erfordern reale Eingaben und fachliche Prüfung.'))+
        '<div class="project-record"><h3>'+t('来源不可用时怎样呈现','How an unavailable source appears','Darstellung bei nicht verfügbarer Quelle')+'</h3><p>'+(state.sourceFailed?t('示例来源读取失败。对应结果保持“待核验”，不能显示为已放行。','Example source unavailable. The result stays pending and cannot be shown as released.','Beispielquelle nicht verfügbar. Das Ergebnis bleibt offen und gilt nicht als freigegeben.'):t('点击可模拟数据来源不可用的状态，不会发起网络请求。','Simulate an unavailable data source without a network request.','Eine nicht verfügbare Datenquelle ohne Netzwerkanfrage simulieren.'))+'</p>'+btn(state.sourceFailed?t('恢复示例来源','Restore example source','Beispielquelle wiederherstellen'):t('模拟来源不可用','Simulate unavailable source','Quellenausfall simulieren'),'source-failure','small',state.sourceFailed?'undo':'warning')+'</div>',
        btn(t('返回项目','Return to project','Zurück zum Projekt'),'close'));
    } else if(state.overlay==='project') {
      html=dialog(t('项目设置','Project settings','Projekteinstellungen'),t('独立于账户与界面语言','Independent of account and interface language','Unabhängig von Konto und Oberflächensprache'),
        '<div class="data-row"><span>'+t('项目','Project','Projekt')+'</span><strong>'+projectName()+'</strong></div><div class="data-row"><span>'+t('示例建筑','Sample building','Beispielgebäude')+'</span><strong>'+t('里昂，法国','Lyon, France','Lyon, Frankreich')+'</strong></div><label class="field" for="settings-country" style="margin-top:20px"><span>'+t('项目国家','Project country','Projektland')+'</span><select id="settings-country">'+countryOptions()+'</select></label><p class="field-hint">'+t('切换国家仅演示国家数据独立存储。不会把示例仓库搬到真实坐标，也不加载当地规则。','Changing country demonstrates separate country data only. It does not move the sample building to real coordinates or load local rules.','Ein Länderwechsel zeigt nur getrennt gespeicherte Länderdaten. Er verschiebt das Beispielgebäude nicht an reale Koordinaten und lädt keine lokalen Regeln.')+'</p>',
        btn(t('取消','Cancel','Abbrechen'),'close')+btn(t('应用国家','Apply country','Land übernehmen'),'apply-country','primary'));
    } else if(state.overlay==='saved') {
      html=dialog(t('已保存项目','Saved projects','Gespeicherte Projekte'),t('账户区预览 · 仅本次浏览器预览内存','Account area preview · This preview session memory only','Vorschau des Kontobereichs · Nur Arbeitsspeicher dieser Vorschau'),
        '<div class="reference-note">'+t('此预览未连接账户。保存、报告和询盘演示仅在当前页面内有效，刷新后会清空。','This preview is not connected to an account. Saves, reports and inquiry previews last only on this page and are cleared on refresh.','Diese Vorschau ist mit keinem Konto verbunden. Gespeicherte Eingaben, Berichte und Anfragevorschauen gelten nur auf dieser Seite und gehen beim Neuladen verloren.')+'</div>'+(state.saved?'<div class="project-record"><h3>'+projectName()+'</h3><p>'+esc(countryName(state.saved.input.country))+' · v'+state.saved.revision+' · '+n(count(state.saved.input))+' '+t('块组件','modules','Module')+'</p><p>'+t('恢复这些输入后可继续编辑，已有报告仍保留。','Restore these inputs to continue editing; existing reports stay available.','Mit diesen Eingaben weiterarbeiten; vorhandene Berichte bleiben erhalten.')+'</p>'+btn(t('恢复这个版本','Restore these inputs','Diese Eingaben wiederherstellen'),'restore','small','undo')+'</div>':'<div class="empty-state">'+icon('save')+'<h3>'+t('还没有保存示例','No saved example yet','Noch kein gespeichertes Beispiel')+'</h3><p>'+t('可先保存当前项目，再修改并恢复，体验返回项目的流程。','Save the project, then edit and restore it to try the return flow.','Projekt speichern, ändern und wiederherstellen, um den Wiedereinstieg zu testen.')+'</p></div>'),
        btn(t('保存当前示例','Save current example','Aktuelles Beispiel speichern'),'save','primary','save'),'drawer');
    } else if(state.overlay==='genie') {
      var gRun=currentRun()||latestRun();
      html=dialog(t('询问 Genie','Ask Genie','Genie fragen'),t('脚本演示 · 未调用 AI','Scripted preview · No AI call','Vordefinierte Vorschau · Kein KI-Aufruf'),
        '<div class="chat-identity"><span class="mark">'+icon('spark')+'</span><div><strong>Genie</strong><p class="small-text">'+t('Linker 的 AI 助手 · 此处为示例回复','Linker’s AI assistant · Example responses here','Der KI-Assistent von Linker · Hier mit Beispielantworten')+'</p></div></div><div class="chat-bubble">'+(gRun?t('我正在查看报告','I am viewing report','Ich betrachte den Bericht')+' '+runLabel(gRun)+t('：',': ',': ')+n(count(gRun.input))+' '+t('块参考组件，','reference modules, ','Referenzmodule, ')+n(capacity(gRun.input),2)+' kWp'+t('。','.','. ')+(stale(gRun)?t('项目输入已修改，这份报告需要更新。',' Project inputs have changed; this report needs updating.',' Die Projekteingaben wurden geändert; der Bericht muss aktualisiert werden.'):t('设备适配、当地要求与发电量仍未核验。',' Equipment compatibility, local requirements and yield remain unverified.',' Gerätekompatibilität, lokale Anforderungen und Ertrag sind noch ungeprüft.')):t('我可以在同一个项目里说明屋顶、设备和报告的关系。先生成报告预览，就能看到我引用的具体版本。','I can explain the roof, system options and report within this project. Create a report preview to see the exact version referenced.','Ich kann Dach, Systemvarianten und Bericht in diesem Projekt erläutern. Eine Berichtsvorschau zeigt die konkret verwendete Version.'))+'</div>'+state.chat.map(function(msg){return '<div class="chat-bubble '+(msg.user?'user':'')+'">'+esc(msg.text)+'</div>';}).join('')+'<form id="chat-form" class="chat-input"><input id="chat-question" aria-label="'+t('输入示例问题','Enter an example question','Beispielfrage eingeben')+'" placeholder="'+t('例如：为什么还不能确定电池？','e.g. Why is the battery still open?','z. B. Warum steht der Speicher noch nicht fest?')+'"><button class="button primary" type="submit" aria-label="'+t('查看示例回答','Show example response','Beispielantwort anzeigen')+'">'+icon('arrow')+'</button></form><p class="field-hint">'+t('回答为预设文本。这里不会调用现有 Genie 或改动产品草稿。','Responses are predefined. This does not call the current Genie or alter product drafts.','Antworten sind vordefiniert. Diese Vorschau ist nicht mit Genie verbunden. Produktentwürfe bleiben unverändert.')+'</p>',null,'drawer');
    } else if(state.overlay==='draft') {
      if(!state.draft) {
        html=dialog(t('Solution draft · 方案草稿','Solution draft','Lösungsentwurf'),t('站点工作清单预览','Site working-list preview','Vorschau der Arbeitsliste'),
          '<div class="empty-state">'+icon('draft')+'<h3>'+t('先将报告版本带入草稿','Add a report version first','Zuerst eine Berichtsversion übernehmen')+'</h3><p>'+t('草稿会同时保留物料、项目版本及待核验说明。这里不会写入真实 WooCommerce 草稿。','The draft retains materials, project version and open checks. Nothing is written to the real WooCommerce draft.','Der Entwurf behält Stückliste, Projektversion und offene Prüfungen. Der echte WooCommerce-Entwurf wird nicht verändert.')+'</p>'+btn(run?t('查看报告','View report','Bericht ansehen'):t('生成报告预览','Create report preview','Berichtsvorschau erstellen'),run?'open-report':'run','primary','report')+'</div>',btn(t('关闭','Close','Schließen'),'close'),'drawer');
      } else {
        var d=state.draft, out=stale(d);
        html=dialog(t('Solution draft · 方案草稿','Solution draft','Lösungsentwurf'),t('交接预览 · 未写入真实产品清单','Handoff preview · No real product-list write','Übergabevorschau · Keine Änderung der echten Produktliste'),
          '<div class="project-record"><h3>'+projectName()+'</h3><p>'+runLabel(d)+' · '+esc(countryName(d.input.country))+' · '+candidateName(d.input.candidate)+'</p>'+(out?pill(t('有更新的项目输入','Project inputs have changed','Projekteingaben geändert'),'stale'):pill(t('同一版本已关联','Same version linked','Gleiche Version verknüpft')) )+'</div>'+bomTable(d.input,false)+'<div class="reference-note">'+t('物料与未核验说明一起传递。已选设备、工程组件、待确认项在后续实现中需保持关联。','Materials and open checks travel together. Selected devices, engineering modules and unresolved items must stay linked in implementation.','Stückliste und offene Prüfungen werden gemeinsam übergeben. Gewählte Geräte, technische Module und offene Positionen müssen verknüpft bleiben.')+'</div>',
          btn(t('查看报告','View report','Bericht ansehen'),'open-report')+btn(out?t('先更新报告','Update report first','Zuerst Bericht aktualisieren'):t('预览询盘','Preview inquiry','Anfrage ansehen'),out?'run':'inquiry','primary','arrow'),'drawer');
      }
    } else if(state.overlay==='inquiry') {
      var d=state.draft;
      if(!d || stale(d)) {
        html=dialog(t('项目询盘预览','Project inquiry preview','Vorschau der Projektanfrage'),t('此入口展示后续交接，不提交任何内容','This previews the handoff and submits nothing','Diese Ansicht zeigt die Übergabe und versendet nichts'),
          '<div class="empty-state">'+icon('report')+'<h3>'+t('先选择当前项目的报告版本','Select a report for the current project','Bericht für das aktuelle Projekt wählen')+'</h3><p>'+t('询盘中应保留对应物料与待核验说明。输入变动后，先更新报告再继续。','The inquiry should retain related materials and open checks. After input changes, update the report before continuing.','Die Anfrage soll die zugehörige Stückliste und offene Prüfungen enthalten. Nach Eingabeänderungen zuerst den Bericht aktualisieren.')+'</p></div>',
          btn(t('返回','Back','Zurück'),'close')+btn(t('生成报告预览','Create report preview','Berichtsvorschau erstellen'),'run','primary'));
      } else {
        html=dialog(t('让团队接着这个项目沟通','Continue this project with the team','Das Projekt mit dem Team weiter besprechen'),t('询盘页预览 · 无需账号 · 本示例不会发送','Inquiry preview · No account required · Nothing is sent','Anfragevorschau · Ohne Konto · Es wird nichts versendet'),
          '<div class="entry-grid"><form id="inquiry-form"><label class="field" for="inquiry-email"><span>'+t('邮箱','Email','E-Mail')+'</span><input id="inquiry-email" type="email" value="installer@example.com" required></label><label class="field" for="inquiry-name"><span>'+t('姓名','Name','Name')+'</span><input id="inquiry-name" value="'+t('示例安装商','Example installer','Beispiel-Installateur')+'" required></label><label class="field" for="inquiry-company"><span>'+t('公司（选填）','Company (optional)','Unternehmen (optional)')+'</span><input id="inquiry-company" value="Example Energy"></label><label class="field" for="inquiry-message"><span>'+t('希望团队协助什么？','What would you like help with?','Wobei dürfen wir Sie unterstützen?')+'</span><textarea id="inquiry-message">'+t('请协助核验设备选型及尚未确认的项目条件。','Please help verify equipment selection and outstanding project details.','Bitte unterstützen Sie uns bei der Geräteauswahl und den offenen Projektangaben.')+'</textarea></label></form><section class="project-record"><h3>'+t('随询盘一起保留','Retained with the inquiry','Mit der Anfrage gespeichert')+'</h3><p>'+projectName()+' · '+runLabel(d)+'</p><p>'+esc(countryName(d.input.country))+' · '+candidateName(d.input.candidate)+'</p>'+bomTable(d.input,true)+pill(t('工程核验仍未完成','Engineering checks still open','Technische Prüfung weiterhin offen'),'pending')+'</section></div>',
          btn(t('返回草稿','Back to draft','Zurück zum Entwurf'),'draft')+'<button class="button primary" type="submit" form="inquiry-form">'+t('模拟提交 · 不发送','Simulate submission · Nothing sent','Übermittlung simulieren · Kein Versand')+icon('arrow')+'</button>','wide');
      }
    } else if(state.overlay==='receipt') {
      var receipt=state.inquiry;
      html=dialog(t('交接内容预览','Handoff content preview','Vorschau der Übergabedaten'),t('模拟完成 · 没有发送邮件或创建线上询盘','Simulation complete · No email or live inquiry created','Simulation abgeschlossen · Keine E-Mail und keine Live-Anfrage'),
        '<div class="receipt-head"><span class="receipt-icon">'+icon('check')+'</span><h2>'+t('团队交接内容示例','Example handoff to the team','Beispiel für die Übergabe an das Team')+'</h2><p>'+t('方案、物料与缺项使用同一个保留版本。','System option, materials and open checks use the same retained version.','Systemvariante, Stückliste und offene Prüfungen verwenden dieselbe gespeicherte Version.')+'</p></div><div class="data-row"><span>'+t('项目 / 版本','Project / version','Projekt / Version')+'</span><strong>'+projectName()+' · '+runLabel(receipt.run)+'</strong></div><div class="data-row"><span>'+t('联系人','Contact','Kontakt')+'</span><strong>'+esc(receipt.name)+'<br>'+esc(receipt.email)+'</strong></div><div class="data-row"><span>'+t('公司','Company','Unternehmen')+'</span><strong>'+esc(receipt.company||'—')+'</strong></div><div class="data-row"><span>'+t('留言','Message','Nachricht')+'</span><strong>'+esc(receipt.message||'—')+'</strong></div>'+bomTable(receipt.run.input,false)+'<div class="reference-note">'+t('这是同一份交接内容的预览。真实的团队通知、询盘状态、价格、Proforma 与邮件仍使用站点业务链，需在正式重构时集成验证。','This previews one handoff record. Real team notifications, inquiry status, prices, Proforma and email remain part of the site commerce flow and require integration verification.','Dies ist die Vorschau eines Übergabedatensatzes. Echte Team-Benachrichtigungen, Anfragestatus, Preise, Proforma und E-Mails bleiben Teil des Website-Ablaufs und sind bei der Integration zu prüfen.')+'</div>',btn(t('返回项目','Return to project','Zurück zum Projekt'),'close','primary'));
    } else if(state.overlay==='progress') {
      var phases=[t('保留当前输入版本','Retain the current input version','Aktuelle Eingabeversion festhalten'),t('整理示例排布与物料','Assemble example layout and materials','Beispielbelegung und Stückliste zusammenstellen'),t('保留未计算与待核验项','Retain uncalculated and open items','Nicht berechnete und offene Punkte festhalten')];
      html=dialog(t('正在准备报告预览','Preparing report preview','Berichtsvorschau wird vorbereitet'),t('界面状态演示，没有运行工程引擎','Interface-state demonstration; no engineering engine is running','Demonstration des UI-Zustands; keine technische Berechnung'),
        '<div class="progress-bar"><span style="width:'+Math.min(100,state.progress*34)+'%"></span></div>'+phases.map(function(p,i){return '<div class="task-phase '+(state.progress>i?'done':'')+'">'+(state.progress>i?icon('check'):'<i class="spinner"></i>')+p+'</div>';}).join(''),null);
    } else if(state.overlay==='state') {
      html=dialog(t('原型当前状态','Current prototype state','Aktueller Prototypstatus'),t('用于评审界面与版本行为','For reviewing the interface and version behaviour','Zur Prüfung von Oberfläche und Versionsverhalten'),
        '<div class="data-row"><span>'+t('布局 / 工作区','Layout / workspace','Layout / Bereich')+'</span><strong>'+state.variant+' / '+state.workspace+'</strong></div><div class="data-row"><span>'+t('项目国家 / 界面语言','Project country / interface language','Projektland / Oberflächensprache')+'</span><strong>'+state.country+' / '+state.lang+'</strong></div><div class="data-row"><span>'+t('输入版本','Input version','Eingabeversion')+'</span><strong>v'+state.revision+'</strong></div><div class="data-row"><span>'+t('最近报告','Latest report','Letzter Bericht')+'</span><strong>'+runLabel(latestRun())+'</strong></div><div class="data-row"><span>'+t('草稿关联','Draft link','Entwurfsbezug')+'</span><strong>'+(state.draft?runLabel(state.draft):'—')+'</strong></div><div class="data-row"><span>'+t('示例保存','Example save','Beispielspeicherung')+'</span><strong>'+(state.saved?'v'+state.saved.revision:'—')+'</strong></div><p class="field-hint">'+t('所有数据仅在内存中。没有账号、工程、AI、产品草稿、支付或邮件 API 调用。','All data stays in memory. No account, engineering, AI, product-draft, payment or mail APIs are called.','Alle Daten bleiben im Arbeitsspeicher. Es werden keine Konto-, Planungs-, KI-, Produktentwurfs-, Zahlungs- oder Mail-APIs aufgerufen.')+'</p>',btn(t('关闭','Close','Schließen'),'close'));
    }
    overlayRoot.innerHTML=html;
    app.inert=!!state.overlay;
    document.body.style.overflow=state.overlay?'hidden':'';
  }
  function sourceSection(title,copy) { return '<section class="project-record"><h3>'+title+'</h3><p>'+copy+'</p></section>'; }
  function openOverlay(name) {
    opener=document.activeElement;
    state.overlay=name;renderOverlay();
    var dialogEl=overlayRoot.querySelector('.dialog'); if(dialogEl) dialogEl.focus();
  }
  function closeOverlay() {
    state.overlay=null;renderOverlay();
    if(opener&&opener.isConnected)opener.focus();
  }
  function toast(message) {
    var el=document.getElementById('toast');el.textContent=message;el.className='show';
    clearTimeout(toastTimer);toastTimer=setTimeout(function(){el.className='';},3600);
  }
  function changeInputs(changes,roofUndo) {
    if(roofUndo)state.undo.push({width:state.width,length:state.length,disabled:state.disabled.slice(),obstacle:state.obstacle,orientation:state.orientation});
    var changed=Object.keys(changes).some(function(k){return JSON.stringify(state[k])!==JSON.stringify(changes[k]);});
    Object.assign(state,changes);
    if(changed)state.revision++;
  }
  function navigate(workspace) {
    state.workspace=workspace;state.overlay=null;render();window.scrollTo({top:0,behavior:'instant'});
  }
  function changeVariant(v) {
    state.variant=v;
    var params=new URLSearchParams(location.search);params.set('variant',v);params.set('lang',state.lang);
    history.replaceState(null,'',location.pathname+'?'+params.toString());
    render();
  }
  function changeLanguage(lang) {
    clearTimeout(toastTimer);document.getElementById('toast').className='';document.getElementById('toast').textContent='';
    state.lang=lang;state.errors={};
    var params=new URLSearchParams(location.search);params.set('lang',lang);params.set('variant',state.variant);
    history.replaceState(null,'',location.pathname+'?'+params.toString());render();
  }
  function parseDecimal(value) {
    var raw=String(value).trim().replace(/\s/g,'');
    if(!/^\d+(?:[.,]\d+)?$/.test(raw))return NaN;
    return Number(raw.replace(',','.'));
  }
  function createRun() {
    if(state.overlay==='progress')return;
    state.overlay='progress';state.progress=0;
    var frozen={id:state.runs.length+1,revision:state.revision,input:clone(model())};
    renderOverlay();
    setTimeout(function(){state.progress=1;renderOverlay();},220);
    setTimeout(function(){state.progress=2;renderOverlay();},600);
    setTimeout(function(){
      state.progress=3;state.runs.push(frozen);state.activeRun=frozen.id;state.overlay=null;state.workspace='report';render();window.scrollTo({top:0,behavior:'instant'});
      toast(t('示例报告已保留对应输入；工程结果仍待计算。','The example report retains its inputs; engineering results remain uncalculated.','Der Beispielbericht enthält seine Eingaben; technische Ergebnisse sind noch nicht berechnet.'));
    },1100);
  }
  function downloadReport() {
    var paper=document.getElementById('report-paper');
    if(!paper)return;
    var html='<!doctype html><html lang="'+document.documentElement.lang+'"><meta charset="utf-8"><title>'+t('Linker 示例报告','Linker example report','Linker Beispielbericht')+'</title><style>body{font:15px/1.7 system-ui;color:#15352f;max-width:850px;margin:45px auto;padding:20px}button,img{display:none}svg{width:100%;max-height:300px}.data-row{display:flex;justify-content:space-between;padding:12px;border-bottom:1px solid #ddd}.paper-note{padding:16px;background:#fff8e9}table{width:100%;border-collapse:collapse}td,th{text-align:left;border-bottom:1px solid #ddd;padding:12px}small{display:block;color:#657970}.paper-section{font-weight:bold;margin-top:28px}h2{font-size:28px}</style>'+paper.outerHTML+'</html>';
    var url=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));
    var a=document.createElement('a');a.href=url;a.download='linker-example-report-'+runLabel(currentRun()).replace(/[^a-z0-9]/gi,'-')+'.html';a.click();setTimeout(function(){URL.revokeObjectURL(url);},1500);
    toast(t('已导出示例 HTML，不是 PDF 或工程报告。','Example HTML exported; this is not a PDF or engineering report.','Beispiel-HTML exportiert; kein PDF und kein technischer Bericht.'));
  }
  document.addEventListener('click',function(e){
    var panel=e.target.closest('[data-panel]');
    if(panel) {
      var ids=state.disabled.slice(),index=ids.indexOf(panel.dataset.panel);
      if(index<0)ids.push(panel.dataset.panel);else ids.splice(index,1);
      changeInputs({disabled:ids},true);render();
      var newPanel=app.querySelector('[data-panel="'+panel.dataset.panel+'"]');if(newPanel)newPanel.focus({preventScroll:true});
      return;
    }
    var workspace=e.target.closest('[data-workspace]');
    if(workspace){navigate(workspace.dataset.workspace);return;}
    var lang=e.target.closest('[data-lang]');if(lang){changeLanguage(lang.dataset.lang);return;}
    var variant=e.target.closest('[data-variant]');if(variant){changeVariant(variant.dataset.variant);return;}
    var orientation=e.target.closest('[data-orientation]');if(orientation){changeInputs({orientation:orientation.dataset.orientation},true);render();return;}
    var goal=e.target.closest('[data-goal]');if(goal){changeInputs({goal:goal.dataset.goal});render();return;}
    var runButton=e.target.closest('[data-run]');if(runButton){state.activeRun=Number(runButton.dataset.run);render();return;}
    var action=e.target.closest('[data-act]');if(!action){if(e.target.dataset.backdrop&&state.overlay!=='progress')closeOverlay();return;}
    var act=action.dataset.act;
    if(['entries','sources','project','saved','genie','draft','inquiry','state'].includes(act)){openOverlay(act);return;}
    if(act==='close'){closeOverlay();return;}
    if(act==='home-workspace'){navigate('overview');return;}
    if(act.indexOf('open-')===0){navigate(act.slice(5));return;}
    if(act==='next-variant'||act==='prev-variant'){var vi=['A','B','C'].indexOf(state.variant);changeVariant(['A','B','C'][(vi+(act==='next-variant'?1:2))%3]);return;}
    if(act==='iso'||act==='plan'){state.view=act;render();return;}
    if(act==='obstacle'){changeInputs({obstacle:!state.obstacle,disabled:[]},true);render();return;}
    if(act==='undo'){
      var prev=state.undo.pop();if(prev){changeInputs(prev);state.errors={};render();}return;
    }
    if(act==='apply-roof'){
      var rawWidth=document.getElementById('roof-width').value,rawLength=document.getElementById('roof-length').value;
      var width=parseDecimal(rawWidth),length=parseDecimal(rawLength);
      if(!Number.isFinite(width)||!Number.isFinite(length)||width<8||width>60||length<6||length>32){
        state.errors={roof:t('请输入有效尺寸：长度 8–60 m，宽度 6–32 m。','Enter valid dimensions: length 8–60 m and width 6–32 m.','Bitte gültige Maße eingeben: Länge 8–60 m und Breite 6–32 m.'),rawWidth:rawWidth,rawLength:rawLength};
        render();document.getElementById(!Number.isFinite(width)||width<8||width>60?'roof-width':'roof-length').focus();return;
      }
      state.errors={};changeInputs({width:width,length:length,disabled:[]},true);render();toast(t('屋顶与物料数量已同步更新。','Roof layout and material count updated together.','Dachbelegung und Materialanzahl wurden gemeinsam aktualisiert.'));return;
    }
    if(act==='apply-energy'){
      var annual=parseDecimal(document.getElementById('annual-consumption').value),country=document.getElementById('project-country').value;
      if(!Number.isFinite(annual)||annual<1||annual>100000000){state.errors.rawAnnual=document.getElementById('annual-consumption').value;state.errors.energy=t('请输入 1–100,000,000 kWh/年的有效演示值；不要使用千位分隔符。','Enter an example between 1 and 100,000,000 kWh/year without thousands separators.','Bitte einen Beispielwert zwischen 1 und 100.000.000 kWh/Jahr ohne Tausendertrennzeichen eingeben.');render();return;}
      state.errors={};changeInputs({annual:annual,country:country});render();toast(t('项目数据已更新；尚未运行能量计算。','Project details updated; no energy calculation has run.','Projektdaten aktualisiert; es wurde keine Energieberechnung ausgeführt.'));return;
    }
    if(act==='apply-country'){changeInputs({country:document.getElementById('settings-country').value});state.overlay=null;render();return;}
    if(act==='profile'){changeInputs({profile:!state.profile});render();return;}
    if(act.indexOf('candidate-')===0){changeInputs({candidate:act.slice(10)});render();return;}
    if(act==='run'){createRun();return;}
    if(act==='save'){
      state.saved={revision:state.revision,input:clone(model())};render();
      toast(t('已保存到本次预览内存；刷新页面会清空。','Saved in this preview session; refreshing resets it.','In dieser Vorschau gespeichert; Neuladen setzt sie zurück.'));return;
    }
    if(act==='restore'){
      if(state.saved){changeInputs(clone(state.saved.input));state.errors={};state.overlay=null;render();toast(t('已恢复示例输入；原有报告保留。','Example inputs restored; previous reports retained.','Beispieleingaben wiederhergestellt; frühere Berichte bleiben erhalten.'));}return;
    }
    if(act==='source-failure'){state.sourceFailed=!state.sourceFailed;renderOverlay();return;}
    if(act==='entry-home'||act==='entry-product'){
      state.origin=act==='entry-home'?'home':'product';navigate(act==='entry-home'?'roof':'devices');
      toast(t('已切换示例入口，项目保持不变。','Example entry changed; the project is unchanged.','Beispieleinstieg gewechselt; das Projekt bleibt erhalten.'));return;
    }
    if(act==='handoff'){
      var handoffRun=currentRun();
      if(!handoffRun||stale(handoffRun)){toast(t('输入已经改变。请先更新报告预览。','Inputs have changed. Update the report preview first.','Eingaben wurden geändert. Bitte zuerst die Berichtsvorschau aktualisieren.'));return;}
      if(state.draft&&state.draft.id===handoffRun.id)toast(t('该版本已在草稿中，没有重复添加。','This version is already in the draft; no duplicate was added.','Diese Version ist bereits im Entwurf; sie wurde nicht doppelt übernommen.'));
      state.draft=clone(handoffRun);render();openOverlay('draft');return;
    }
    if(act==='export'){downloadReport();return;}
  });
  document.addEventListener('change',function(e){if(e.target.id==='review-language')changeLanguage(e.target.value);});
  document.addEventListener('submit',function(e){
    if(e.target.id==='chat-form'){
      e.preventDefault();var input=document.getElementById('chat-question'),value=input.value.trim();if(!value)return;
      state.chat.push({user:true,text:value});
      state.chat.push({user:false,text:t('示例回答：仅靠屋顶面积或年用电量还不能确定电池。需要负荷时序、目标、功率与容量边界、SOC 策略和厂商兼容依据；缺少的条件应保留在报告中。','Example response: roof area or annual consumption alone cannot size a battery. Load time series, goals, power and capacity limits, SOC strategy and manufacturer compatibility evidence are needed. Missing conditions should remain visible in the report.','Beispielantwort: Dachfläche oder Jahresverbrauch allein reichen nicht zur Speicherauslegung. Benötigt werden Lastzeitreihen, Ziele, Leistungs- und Kapazitätsgrenzen, SOC-Strategie und Hersteller-Kompatibilitätsnachweise. Fehlende Angaben sollen im Bericht sichtbar bleiben.')});
      renderOverlay();var question=document.getElementById('chat-question');if(question)question.focus();return;
    }
    if(e.target.id==='inquiry-form'){
      e.preventDefault();if(!state.draft||stale(state.draft)){openOverlay('inquiry');return;}
      state.inquiry={run:clone(state.draft),name:document.getElementById('inquiry-name').value,email:document.getElementById('inquiry-email').value,company:document.getElementById('inquiry-company').value,message:document.getElementById('inquiry-message').value};
      openOverlay('receipt');
    }
  });
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&state.overlay&&state.overlay!=='progress'){closeOverlay();return;}
    if(state.overlay){
      if(e.key==='Tab'){
        var focusable=Array.from(overlayRoot.querySelectorAll('button:not(:disabled),input,select,textarea,[tabindex="0"]')).filter(function(el){return el.getClientRects().length;});
        if(!focusable.length){e.preventDefault();return;}
        var first=focusable[0],last=focusable[focusable.length-1];
        if(e.shiftKey&&(document.activeElement===first||document.activeElement.classList.contains('dialog'))){e.preventDefault();last.focus();}
        else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
      }
      return;
    }
    if(e.target.closest('input,textarea,select,[contenteditable="true"]'))return;
    if(e.target.closest('[data-panel]')&&(e.key==='Enter'||e.key===' ')){e.preventDefault();e.target.closest('[data-panel]').dispatchEvent(new MouseEvent('click',{bubbles:true}));return;}
    if(e.key==='ArrowLeft'||e.key==='ArrowRight'){
      e.preventDefault();var vi=['A','B','C'].indexOf(state.variant);changeVariant(['A','B','C'][(vi+(e.key==='ArrowRight'?1:2))%3]);
    }
  });
  render();
})();
