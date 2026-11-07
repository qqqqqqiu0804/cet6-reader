/* 英语六级真题解析 · 随身读 — mobile reader */
(function(){
  'use strict';
  const MANIFEST_URL = 'img/manifest.json';
  const IMG_BASE = 'img/';
  const LS_KEY = 'cet6-progress-v1';
  const LS_RECENT = 'cet6-recent-v1';

  let MANIFEST = null;
  let progress = loadJSON(LS_KEY, {});   // slug -> page_idx(0-based)
  let recents = loadJSON(LS_RECENT, []); // [{slug,name,page}]

  // current reader state
  let cur = { slug:null, name:null, pages:0, dir:null, loaded:0, imgs:[] };

  /* ---------- storage ---------- */
  function loadJSON(k, def){ try{ return JSON.parse(localStorage.getItem(k)) ?? def; }catch(e){ return def; } }
  function saveProgress(){ localStorage.setItem(LS_KEY, JSON.stringify(progress)); }
  function saveRecents(){
    recents = recents.slice(0,8);
    localStorage.setItem(LS_RECENT, JSON.stringify(recents));
  }
  function pushRecent(slug, name, page){
    recents = recents.filter(r => r.slug !== slug);
    recents.unshift({slug, name, page});
    saveRecents();
  }

  /* ---------- boot ---------- */
  fetch(MANIFEST_URL, {cache:'no-cache'})
    .then(r => r.json())
    .then(m => { MANIFEST = m; renderHome(); })
    .catch(e => {
      document.getElementById('terms').innerHTML =
        '<div class="loading">无法加载清单：'+e.message+'</div>';
    });

  /* ---------- home ---------- */
  function renderHome(){
    const resume = document.getElementById('resume');
    if (recents.length){
      const r = recents[0];
      resume.innerHTML =
        '<div class="resume"><div class="rinfo"><div class="rt">'+esc(r.name)+
        '</div><div class="rs">上次读到第 '+(r.page+1)+' 页</div></div>'+
        '<button class="rgo" id="resumeGo">继续</button></div>';
      document.getElementById('resumeGo').onclick = () => openDoc(r.slug, r.page);
    } else { resume.innerHTML = ''; }

    const wrap = document.getElementById('terms');
    wrap.innerHTML = '';
    MANIFEST.terms.forEach(term => {
      const el = document.createElement('div');
      el.className = 'term';
      const filesHtml = term.files.map(f => {
        const pct = progress[f.slug] != null ? Math.round((progress[f.slug]+1)/f.pages*100) : 0;
        return '<button class="file" data-slug="'+f.slug+'">'+
          '<span class="ft a">解</span>'+
          '<span class="fi"><span class="fn">'+esc(f.name)+'</span>'+
          '<span class="fp">'+f.pages+' 页 · 答案解析</span>'+
          (pct>0?'<span class="prog"><i style="width:'+pct+'%"></i></span>':'')+
          '</span><span class="farrow">›</span></button>';
      }).join('');
      el.innerHTML =
        '<div class="thead"><span class="tl">'+esc(term.label)+'</span>'+
        '<span class="badge">'+term.files.length+' 份</span></div>'+
        '<div class="tbody"><div class="flist">'+filesHtml+'</div></div>';
      el.querySelector('.thead').onclick = () => el.classList.toggle('open');
      el.querySelectorAll('.file').forEach(b => {
        b.onclick = () => {
          const slug = b.dataset.slug;
          const f = term.files.find(x=>x.slug===slug);
          openDoc(slug, progress[slug] || 0, f);
        };
      });
      wrap.appendChild(el);
    });
    // open the first term by default
    if (wrap.firstChild) wrap.firstChild.classList.add('open');
  }

  // search
  document.getElementById('search').addEventListener('input', function(){
    const q = this.value.trim().toLowerCase();
    document.querySelectorAll('.term').forEach(t => {
      let hit = false;
      t.querySelectorAll('.file').forEach(f => {
        const name = f.querySelector('.fn').textContent.toLowerCase();
        const ok = !q || name.includes(q);
        f.style.display = ok ? '' : 'none';
        if (ok) hit = true;
      });
      t.style.display = hit ? '' : 'none';
      if (hit && q) t.classList.add('open');
    });
  });

  /* ---------- reader ---------- */
  function openDoc(slug, pageIdx, fileMeta){
    if (!fileMeta){
      for (const t of MANIFEST.terms)
        for (const f of t.files) if (f.slug===slug){ fileMeta=f; break; }
    }
    if (!fileMeta) return;
    cur = { slug, name:fileMeta.name, pages:fileMeta.pages, dir:fileMeta.dir, loaded:0, imgs:[] };
    document.getElementById('readerTitle').textContent = fileMeta.name;
    document.getElementById('pageLabel').textContent = '1 / '+fileMeta.pages;
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('scroll').innerHTML = '';
    buildDrawer();
    showReader(true);
    loadTo(pageIdx + 4);   // eager ahead
    goPage(pageIdx);
  }

  function pageUrl(i){
    // i is 1-based
    return IMG_BASE + cur.dir.split('/').pop() + '/' + String(i).padStart(3,'0') + '.jpg';
  }

  function loadTo(targetIdx){ // targetIdx is 0-based inclusive
    const scroll = document.getElementById('scroll');
    const need = Math.min(targetIdx, cur.pages-1);
    while (cur.loaded <= need){
      const p = cur.loaded + 1;
      const fig = document.createElement('figure');
      const img = document.createElement('img');
      img.loading = 'lazy';
      img.decoding = 'async';
      img.dataset.idx = p;
      img.alt = '第'+p+'页';
      img.src = pageUrl(p);
      img.onerror = () => { img.style.minHeight='120px'; img.alt='图片加载失败: '+pageUrl(p); };
      fig.appendChild(img);
      scroll.appendChild(fig);
      cur.imgs[p] = img;
      cur.loaded++;
    }
  }

  let curPage = 0;
  function goPage(idx){
    idx = Math.max(0, Math.min(cur.pages-1, idx));
    curPage = idx;
    loadTo(idx + 4);
    loadTo(idx - 2);
    const el = cur.imgs[idx+1];
    if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
    document.getElementById('pageLabel').textContent = (idx+1)+' / '+cur.pages;
    const pctr = (idx+1)/cur.pages*100;
    document.getElementById('progressBar').style.width = pctr+'%';
    progress[cur.slug] = idx;
    saveProgress();
    pushRecent(cur.slug, cur.name, idx);
  }

  function showReader(on){
    document.getElementById('reader').classList.toggle('show', on);
    document.body.style.overflow = on ? 'hidden' : '';
  }

  /* reader controls */
  document.getElementById('btnBack').onclick = () => showReader(false);
  document.getElementById('btnTop').onclick = () => goPage(0);
  document.getElementById('btnDir').onclick = () => document.getElementById('drawer').classList.add('show');
  document.getElementById('drawerMask').onclick = () => document.getElementById('drawer').classList.remove('show');
  document.getElementById('btnZoom').onclick = () => {
    const on = document.getElementById('btnZoom').classList.toggle('active');
    document.getElementById('scroll').querySelectorAll('img').forEach(i=>i.classList.toggle('zoom', on));
    if (on) document.getElementById('scroll').style.overflowX='auto';
    else document.getElementById('scroll').style.overflowX='';
  };
  document.getElementById('btnGo').onclick = submitGo;
  document.getElementById('pageInput').addEventListener('keydown', e=>{ if(e.key==='Enter') submitGo(); });
  function submitGo(){
    const v = parseInt(document.getElementById('pageInput').value,10);
    if (!isNaN(v)) goPage(v-1);
    document.getElementById('pageInput').value='';
  }

  // scroll -> update current page + lazy-load
  const scrollEl = document.getElementById('scroll');
  let ticking = false;
  scrollEl.addEventListener('scroll', () => {
    if (ticking) return; ticking = true;
    requestAnimationFrame(() => {
      const mid = scrollEl.scrollTop + scrollEl.clientHeight*0.4;
      let idx = 0;
      for (let p=1; p<=cur.pages; p++){
        const im = cur.imgs[p];
        if (!im) break;
        if (im.offsetTop <= mid) idx = p-1;
      }
      if (idx !== curPage){
        curPage = idx;
        document.getElementById('pageLabel').textContent = (idx+1)+' / '+cur.pages;
        document.getElementById('progressBar').style.width = ((idx+1)/cur.pages*100)+'%';
        progress[cur.slug] = idx; saveProgress();
        loadTo(idx + 4); loadTo(idx - 2);
        pushRecent(cur.slug, cur.name, idx);
      }
      ticking = false;
    });
  });

  // keyboard (desktop)
  document.addEventListener('keydown', e => {
    if (!document.getElementById('reader').classList.contains('show')) return;
    if (e.key==='ArrowDown'||e.key===' ') { e.preventDefault(); goPage(curPage+1); }
    else if (e.key==='ArrowUp') { e.preventDefault(); goPage(curPage-1); }
    else if (e.key==='Escape') showReader(false);
  });

  /* drawer */
  function buildDrawer(){
    const list = document.getElementById('drawerList');
    list.innerHTML = '';
    MANIFEST.terms.forEach(t => {
      t.files.forEach(f => {
        const d = document.createElement('div');
        d.className = 'item' + (f.slug===cur.slug?' cur':'');
        const read = progress[f.slug]!=null?(' · 已读'+(progress[f.slug]+1)):'';
        d.textContent = f.name + '  ('+f.pages+'页'+read+')';
        d.onclick = () => {
          document.getElementById('drawer').classList.remove('show');
          if (f.slug===cur.slug) scrollEl.scrollTo({top:0,behavior:'smooth'});
          else openDoc(f.slug, progress[f.slug]||0, f);
        };
        list.appendChild(d);
      });
    });
  }

  /* utils */
  function esc(s){ return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

  /* PWA service worker */
  if ('serviceWorker' in navigator){
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(()=>{});
    });
  }
})();
