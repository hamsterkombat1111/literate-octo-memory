// === Background particles ===
const canvas = document.getElementById('bg');
const ctx = canvas.getContext('2d');
function size(){ canvas.width = innerWidth; canvas.height = innerHeight; }
size(); addEventListener('resize', size);

const N = 70;
const pts = Array.from({length:N}, () => ({
  x: Math.random()*canvas.width,
  y: Math.random()*canvas.height,
  vx: (Math.random()-.5)*.6,
  vy: (Math.random()-.5)*.6
}));

function draw(){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.fillStyle = 'rgba(17,20,31,0.85)';
  ctx.fillRect(0,0,canvas.width,canvas.height);

  pts.forEach(p=>{
    p.x+=p.vx; p.y+=p.vy;
    if(p.x<0||p.x>canvas.width) p.vx*=-1;
    if(p.y<0||p.y>canvas.height) p.vy*=-1;
  });

  for(let i=0;i<N;i++){
    for(let j=i+1;j<N;j++){
      const a=pts[i], b=pts[j];
      const dx=a.x-b.x, dy=a.y-b.y;
      const d=Math.hypot(dx,dy);
      if(d<120){
        ctx.strokeStyle = 'rgba(93,170,255,'+(1-d/120)*0.25+')';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
      }
    }
  }
  ctx.fillStyle = '#9ed1ff';
  pts.forEach(p=>{ ctx.beginPath(); ctx.arc(p.x,p.y,1.7,0,Math.PI*2); ctx.fill(); });
  requestAnimationFrame(draw);
}
draw();

// === Анимация появления секций ===
const observer = new IntersectionObserver(es=>{
  es.forEach(e=>{ if(e.isIntersecting) e.target.classList.add('visible'); });
},{threshold:.2});
document.querySelectorAll('.fade-in').forEach(el=>observer.observe(el));

// === Ripple эффект для кнопок ===
function ripple(el){ el.classList.remove('rippling'); void el.offsetWidth; el.classList.add('rippling'); }
document.querySelectorAll('.btn').forEach(b=>b.addEventListener('click',()=>ripple(b)));

// === База программ ===
const programsData = {
  network: [
    { name:'Ingram', info:'Сетевой сканер • 50 MB • v3.1', tags:['Windows','CLI'], link:'#', more:'#' },
    { name:'KPortScan', info:'Порт-сканер • 15 MB • v1.0', tags:['Multi-OS'], link:'#', more:'#' },
    { name:'NetProbe', info:'Мониторинг сети • 28 MB • v2.4', tags:['GUI'], link:'#', more:'#' }
  ],
  media: [
    { name:'SoundPad', info:'Аудио тул • 12 MB • v1.5', tags:['Windows'], link:'#', more:'#' },
    { name:'Noon', info:'Видео утилита • 30 MB • v2.0', tags:['Multi-OS'], link:'#', more:'#' }
  ],
  system: [
    { name:'SmartPSS', info:'Системная утилита • 35 MB • v2.0', tags:['Windows'], link:'#', more:'#' },
    { name:'MVFPS', info:'Менеджер • 25 MB • v1.3', tags:['Windows','Portable'], link:'#', more:'#' }
  ],
  joke: [
    { name:'хз, дристня какаята', info:'Системная утилита • 999999 TB • v2.0', tags:['Windows'], link:'#', more:'#' },
    { name:'шо эта такэ', info:'Менеджер • 99999 TB • v1.3', tags:['Windows','Portable'], link:'google.com', more:'arkadacore.txt' }
  ]
};

const programsEl = document.querySelector('.programs');
const chips = document.querySelectorAll('.chip');
const q = document.getElementById('q');
const viewSegs = document.querySelectorAll('.seg');

let currentCategory = 'network';
let currentView = 'grid';
if (programsEl) renderPrograms();

chips.forEach(ch=>ch.addEventListener('click',()=>{
  chips.forEach(c=>c.classList.remove('is-active'));
  ch.classList.add('is-active');
  currentCategory = ch.dataset.category;
  renderPrograms();
}));

if (q) q.addEventListener('input',()=>renderPrograms());
viewSegs.forEach(s=>s.addEventListener('click',()=>{
  viewSegs.forEach(x=>x.classList.remove('on'));
  s.classList.add('on');
  currentView = s.dataset.view;
  renderPrograms();
}));

function renderPrograms(){
  const dataset = programsData[currentCategory] || [];
  const needle = (q?.value||'').toLowerCase().trim();
  const filtered = dataset.filter(p=>p.name.toLowerCase().includes(needle));

  programsEl.classList.toggle('list', currentView==='list');
  programsEl.classList.toggle('grid', currentView==='grid');
  programsEl.innerHTML = '';

  filtered.forEach((p, idx)=>{
    const card = document.createElement('div');
    card.className = 'program';
    card.style.animation = `fadeIn .4s ease ${idx*40}ms both`;
    card.innerHTML = `
      <h4>${p.name}</h4>
      <div class="meta">${p.info}</div>
      ${p.tags?.length ? `<div class="tag">${p.tags.join(' • ')}</div>`:''}
    `;
    card.addEventListener('click',()=>openModal(p));
    programsEl.appendChild(card);
  });
}

// === Modal ===
const modal = document.getElementById('modal');
const modalTitle = document.getElementById('modal-title');
const modalInfo = document.getElementById('modal-info');
const downloadBtn = document.getElementById('download-btn');
const moreBtn = document.getElementById('more-btn');
const tagsEl = document.getElementById('tags');

function openModal(p){
  modal.style.display = 'flex';
  modalTitle.textContent = p.name;
  modalInfo.textContent = p.info;
  downloadBtn.href = p.link || '#';
  moreBtn.href = p.more || '#';
  tagsEl.innerHTML = (p.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('');
}
document.querySelector('.close').addEventListener('click',()=>modal.style.display='none');
document.getElementById('close-btn').addEventListener('click',()=>modal.style.display='none');
addEventListener('click',e=>{ if(e.target===modal) modal.style.display='none'; });

/* === Псевдо-страницы: переключение без скролла === */
const pages = Array.from(document.querySelectorAll('.page'));
const navItems = Array.from(document.querySelectorAll('[data-page]'));

let softInitDone = false; // чтобы инициализировать сетку софта один раз

function setActiveNav(pageId){
  navItems.forEach(a => a.classList.toggle('active', a.dataset.page === pageId));
}

function showPage(pageId){
  pages.forEach(sec => {
    if(sec.id === pageId){
      // сначала делаем display:block, затем даём кадр на анимацию
      sec.classList.add('active');
    }else{
      sec.classList.remove('active');
    }
  });

  setActiveNav(pageId);

  // лениво инициализируем страницу "Софт" (если надо)
  if(pageId === 'soft' && !softInitDone){
    // если твой код рендеринга уже вызван — просто помечаем флаг
    // если нет — можно принудительно дернуть:
    try { typeof renderPrograms === 'function' && renderPrograms(); } catch(_){}
    softInitDone = true;
  }

  // обновляем hash, чтобы можно было делиться ссылкой на раздел
  if(location.hash.replace('#','') !== pageId){
    history.replaceState(null, '', '#'+pageId);
  }
}

// перехватываем клики по меню и кнопкам на главной
navItems.forEach(a=>{
  a.addEventListener('click', e=>{
    const target = a.dataset.page;
    if(!target) return;
    e.preventDefault();
    showPage(target);
  });
});

// стартовая секция — из hash либо home
const start = location.hash.replace('#','') || 'home';
showPage(start);

// если пользователь вручную меняет hash (например, из закладки)
window.addEventListener('hashchange', ()=>{
  const id = location.hash.replace('#','') || 'home';
  showPage(id);
});

// ===== SAFE ENHANCER FOR MODAL (versions + VirusTotal + download sheet) =====
document.addEventListener('DOMContentLoaded', () => {
  const $ = (id) => document.getElementById(id);

  // Базовые элементы модалки (должны уже быть в твоём HTML)
  const modal       = $('modal');
  const modalTitle  = $('modal-title');
  const modalInfo   = $('modal-info');
  const tagsEl      = $('tags');
  const downloadBtn = $('download-btn');
  const moreBtn     = $('more-btn');

  // Если базовой модалки нет — тихо выходим, чтобы не ломать сайт
  if (!modal || !modalTitle || !modalInfo || !downloadBtn || !moreBtn || !tagsEl) return;

  // НЕобязательные новые элементы (если их нет — просто отключим фичу)
  const vtBtn    = $('vt-btn') || null;

  // Версии (dropdown) — опционально
  const verPill  = $('version-pill') || null;
  const verDD    = $('version-dd') || null;

  // Лист вариантов скачивания (sheet) — опционально
  const sheet    = $('dl-sheet') || null;
  const dlDirect = $('dl-direct') || null;
  const dlMega   = $('dl-mega') || null;
  const dlGD     = $('dl-gd') || null;
  const dlClose  = $('dl-close') || null;

  // Флаги наличия UI
  const hasVersionsUI = !!(verPill && verDD);
  const hasSheetUI    = !!(sheet && dlDirect && dlMega && dlGD && dlClose);

  // Текущее состояние
  let currentProgram = null;
  let currentVersionIndex = 0;

  // Построение URL для VirusTotal
  function vtUrlFor(ver){
    if (!ver) return '';
    if (ver.virustotal) return ver.virustotal;
    if (ver.sha256)     return `https://www.virustotal.com/gui/file/${ver.sha256}`;
    return '';
  }

  function setActiveVersion(idx){
    const versions = currentProgram?.versions || [];
    if (!versions.length) return;

    currentVersionIndex = Math.max(0, Math.min(idx, versions.length - 1));
    const ver = versions[currentVersionIndex];

    if (hasVersionsUI) {
      verPill.textContent = ver?.label || '—';
    }

    if (vtBtn) {
      const url = vtUrlFor(ver);
      if (url) { vtBtn.hidden = false; vtBtn.href = url; }
      else { vtBtn.hidden = true; vtBtn.removeAttribute('href'); }
    }
  }

  function fillVersionsDropdown(){
    const versions = currentProgram?.versions || [];
    if (!hasVersionsUI) return;
    if (!versions.length) { verDD.hidden = true; return; }

    verDD.innerHTML = versions.map((v,i)=>`
      <div class="ver-item" data-idx="${i}">
        <div class="ver-label">${v.label}</div>
        <div class="ver-meta">${v.sha256 ? 'sha256' : (v.virustotal ? 'VT' : '')}</div>
      </div>
    `).join('');

    verDD.querySelectorAll('.ver-item').forEach(it=>{
      it.addEventListener('click', ()=>{
        const i = +it.dataset.idx;
        setActiveVersion(i);
        verDD.hidden = true;
        verPill?.setAttribute('aria-expanded','false');
      });
    });
  }

  function openDownloadSheet(){
    if (!hasSheetUI) return; // нет листа — просто выходим
    const versions = currentProgram?.versions || [];
    const ver = versions[currentVersionIndex];

    function setBtn(anchor, url){
      if (!anchor) return;
      if (url) { anchor.hidden = false; anchor.href = url; }
      else { anchor.hidden = true; anchor.removeAttribute('href'); }
    }

    if (ver?.links){
      setBtn(dlDirect, ver.links.direct);
      setBtn(dlMega,   ver.links.mega);
      setBtn(dlGD,     ver.links.gdrive);
    } else {
      // Фоллбек на старый p.link, если кто-то не заполнил версии
      setBtn(dlDirect, currentProgram?.link || '');
      if (dlMega) dlMega.hidden = true;
      if (dlGD)   dlGD.hidden   = true;
    }

    sheet.hidden = false;
  }

  // Подмена поведения кнопки "Скачать" (только если лист есть)
  if (hasSheetUI) {
    downloadBtn.addEventListener('click', (e) => {
      e.preventDefault();
      openDownloadSheet();
    });
    dlClose.addEventListener('click', () => sheet.hidden = true);
    sheet.addEventListener('click', (e)=>{ if (e.target === sheet) sheet.hidden = true; });
  }

  // Триггер dropdown-а версий (если есть UI)
  if (hasVersionsUI) {
    verPill.addEventListener('click', () => {
      const hidden = verDD.hasAttribute('hidden');
      if (hidden) { verDD.hidden = false; verPill.setAttribute('aria-expanded','true'); }
      else { verDD.hidden = true; verPill.setAttribute('aria-expanded','false'); }
    });

    // Закрывать по клику вне dropdown внутри модалки
    document.addEventListener('click', (e)=>{
      if (!modal.contains(e.target)) return;
      if (e.target === verPill) return;
      if (!verDD.hidden && !verDD.contains(e.target)) {
        verDD.hidden = true; verPill.setAttribute('aria-expanded','false');
      }
    });
  }

  // ===== Расширяем существующий openModal, не ломая старый рендер =====
  const prevOpenModal = window.openModal;
  window.openModal = function(p){
    currentProgram = p || {};
    // сначала вызываем твой старый openModal (если он был)
    if (typeof prevOpenModal === 'function') {
      try { prevOpenModal(p); } catch(e) { console.warn('prevOpenModal error:', e); }
    } else {
      // минимальный фоллбек, если старого не было
      modal.style.display = 'flex';
      modalTitle.textContent = p?.name || '';
      modalInfo.textContent  = p?.info || '';
      moreBtn.href = p?.more || '#';
      tagsEl.innerHTML = (p?.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('');
    }

    // ВЕРСИИ
    if (hasVersionsUI && Array.isArray(p?.versions) && p.versions.length){
      verPill.style.display = '';
      setActiveVersion(0);
      fillVersionsDropdown();
    } else if (hasVersionsUI) {
      verPill.style.display = 'none';
      verDD.hidden = true;
      if (vtBtn) { vtBtn.hidden = true; vtBtn.removeAttribute('href'); }
    }

    // Если листа скачивания нет — кнопка "Скачать" остаётся как раньше (href укажет твой старый код)
  };

});


// === Admin avatars (initials; configurable map for custom images) ===
(function(){
  // Map name -> avatar URL (optional). Leave empty to auto-generate initials.
  const AVATAR_URLS = {
    // "Православный Бес": "/avatars/bes.png",
    // "Everyday": "/avatars/everyday.jpg"
  };

  function initialsFromName(name){
    const parts = name.trim().split(/\s+/);
    const letters = (parts[0]?.[0]||"").toUpperCase() + (parts[1]?.[0]||"").toUpperCase();
    return letters || (name[0]||"?").toUpperCase();
  }
  function colorFromString(s){
    let h = 0;
    for (let i=0;i<s.length;i++){ h = (h*31 + s.charCodeAt(i))>>>0; }
    const hue = h % 360;
    return `linear-gradient(135deg, hsl(${(hue+20)%360} 60% 35%), hsl(${(hue+220)%360} 80% 45%))`;
  }

  document.querySelectorAll('.admin-card .admin-name').forEach(nameEl=>{
    const name = nameEl.textContent.trim();
    if (nameEl.previousElementSibling?.classList?.contains('admin-avatar')) return; // already added
    const url = AVATAR_URLS[name];
    let avatar;
    if (url){
      avatar = document.createElement('img');
      avatar.src = url; avatar.alt = name; avatar.className = 'admin-avatar';
      avatar.loading = "lazy"; avatar.decoding = "async";
    } else {
      avatar = document.createElement('div');
      avatar.className = 'admin-avatar';
      avatar.textContent = initialsFromName(name);
      avatar.style.background = colorFromString(name);
    }
    nameEl.parentElement.insertBefore(avatar, nameEl);
  });
})();


// === Mobile nav toggle ===
(function(){
  const header = document.querySelector('header');
  const btn = document.querySelector('.nav-toggle');
  if (btn && header){
    btn.addEventListener('click', ()=> header.classList.toggle('is-open'));
  }
})();

// === Admin avatars (initials; configurable map for custom images) ===
(function(){
  const AVATAR_URLS = {
    // "Православный Бес": "../files/avatars/bes.png",
    // "Everyday": "../files/avatars/everyday.jpg"
  };
  function initialsFromName(name){
    const parts = name.trim().split(/\s+/);
    const letters = (parts[0]?.[0]||"").toUpperCase() + (parts[1]?.[0]||"").toUpperCase();
    return letters || (name[0]||"?").toUpperCase();
  }
  function colorFromString(s){
    let h = 0; for (let i=0;i<s.length;i++){ h = (h*31 + s.charCodeAt(i))>>>0; }
    const hue = h % 360;
    return `linear-gradient(135deg, hsl(${(hue+20)%360} 60% 35%), hsl(${(hue+220)%360} 80% 45%))`;
  }
  document.querySelectorAll('.admin-card .admin-name').forEach(nameEl=>{
    const name = nameEl.textContent.trim();
    if (nameEl.previousElementSibling?.classList?.contains('admin-avatar')) return;
    const url = AVATAR_URLS[name];
    let avatar;
    if (url){
      avatar = document.createElement('img');
      avatar.src = url; avatar.alt = name; avatar.className = 'admin-avatar'; avatar.loading="lazy"; avatar.decoding="async";
    } else {
      avatar = document.createElement('div');
      avatar.className = 'admin-avatar';
      avatar.textContent = initialsFromName(name);
      avatar.style.background = colorFromString(name);
    }
    nameEl.parentElement.insertBefore(avatar, nameEl);
  });
})();
