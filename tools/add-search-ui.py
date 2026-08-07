#!/usr/bin/env python3
"""Inject the site search box, styles and script into every page.

Idempotent - running it twice changes nothing. Re-run after adding a page.
"""
import glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

CSS = """
/* site search */
.search{position:relative;margin:0 0 20px}
.search form{display:flex;gap:8px}
.search input{flex:1;min-width:0;font-family:inherit;font-size:16px;color:var(--ink);
  background:#fff;border:1.5px solid var(--line);border-radius:24px;padding:11px 18px}
.search input::placeholder{color:var(--gray)}
.search input:focus{outline:none;border-color:var(--gold);box-shadow:0 0 0 3px var(--gold-soft)}
.search .clr{display:none;background:none;border:none;color:var(--gray);font-size:22px;
  line-height:1;cursor:pointer;padding:0 6px;font-family:inherit}
.search.on .clr{display:block}
.sres{display:none;position:absolute;z-index:40;left:0;right:0;top:calc(100% + 6px);
  background:#fff;border:1px solid var(--line);border-radius:10px;
  box-shadow:0 12px 34px rgba(29,26,32,.18);max-height:70vh;overflow-y:auto}
.search.on .sres{display:block}
.sres .meta{padding:10px 16px;border-bottom:1px solid var(--line);color:var(--gray);
  font-size:13px;position:sticky;top:0;background:#fff}
.sres a{display:block;padding:11px 16px;border-bottom:1px solid var(--line);
  text-decoration:none;color:var(--ink)}
.sres a:last-child{border-bottom:none}
.sres a:hover,.sres a.sel{background:var(--gold-soft)}
.sres .src{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;
  letter-spacing:.08em;text-transform:uppercase;color:var(--red-deep)}
.sres .src .pg{color:var(--gray);font-weight:400;letter-spacing:.02em;text-transform:none}
.sres .hd{font-weight:600;font-size:15px;margin:1px 0 2px}
.sres .sn{color:var(--gray);font-size:13.5px;line-height:1.45}
.sres mark{background:var(--gold-soft);color:var(--ink);font-weight:600;padding:0 1px}
.sres .none{padding:16px;color:var(--gray);font-size:14px}
@media (max-width:560px){.sres{max-height:60vh}.search input{font-size:16px}}
"""

MARKUP = """<div class="search" id="sitesearch">
  <form role="search" onsubmit="return false">
    <input type="search" id="sq" autocomplete="off" placeholder="Search the site and every PDF…"
           aria-label="Search the site and PDFs" aria-controls="sres">
    <button type="button" class="clr" id="sclr" aria-label="Clear search">&times;</button>
  </form>
  <div class="sres" id="sres" role="listbox" aria-label="Search results"></div>
</div>
"""

JS = """
/* site search */
(function(){
  var box=document.getElementById('sitesearch'), q=document.getElementById('sq'),
      out=document.getElementById('sres'), clr=document.getElementById('sclr');
  if(!box||!q||!out) return;
  var idx=null, loading=false, sel=-1, depth=(location.pathname.split('/').length,'');
  function esc(s){return s.replace(/[&<>"]/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function load(cb){
    if(idx){cb();return;}
    if(loading) return;
    loading=true;
    out.innerHTML='<div class="none">Loading…</div>'; box.classList.add('on');
    fetch('search-index.json').then(function(r){return r.json();}).then(function(d){
      idx=d; loading=false; cb();
    }).catch(function(){
      loading=false;
      out.innerHTML='<div class="none">Search index could not load.</div>';
    });
  }
  function snippet(text, terms){
    var low=text.toLowerCase(), at=-1;
    for(var i=0;i<terms.length;i++){var p=low.indexOf(terms[i]); if(p>=0&&(at<0||p<at)) at=p;}
    if(at<0) at=0;
    var s=Math.max(0, at-70), e=Math.min(text.length, at+180);
    var frag=(s>0?'…':'')+text.slice(s,e)+(e<text.length?'…':'');
    frag=esc(frag);
    terms.forEach(function(t){
      if(!t) return;
      frag=frag.replace(new RegExp('('+t.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&')+')','ig'),'<mark>$1</mark>');
    });
    return frag;
  }
  function run(){
    var raw=q.value.trim();
    if(raw.length<2){box.classList.remove('on'); out.innerHTML=''; return;}
    load(function(){
      var terms=raw.toLowerCase().split(/\\s+/).filter(Boolean),
          phrase=raw.toLowerCase(), hits=[];
      idx.r.forEach(function(r){
        var x=r.x.toLowerCase(), h=(r.h||'').toLowerCase(), s=(r.s||'').toLowerCase(), sc=0, all=true;
        terms.forEach(function(t){
          var n=x.split(t).length-1;
          if(!n && h.indexOf(t)<0 && s.indexOf(t)<0){all=false; return;}
          sc+=Math.min(n,8);
          if(h.indexOf(t)>=0) sc+=14;
          if(s.indexOf(t)>=0) sc+=8;
        });
        if(!all) return;
        if(x.indexOf(phrase)>=0) sc+=25;
        if(h.indexOf(phrase)>=0) sc+=30;
        if(r.k==='page') sc+=6;
        hits.push({r:r,sc:sc});
      });
      hits.sort(function(a,b){return b.sc-a.sc;});
      hits=hits.slice(0,25);
      if(!hits.length){
        out.innerHTML='<div class="none">Nothing found for “'+esc(raw)+'”.</div>';
        box.classList.add('on'); return;
      }
      var np=hits.filter(function(h){return h.r.k==='pdf';}).length;
      var html='<div class="meta">'+hits.length+' result'+(hits.length===1?'':'s')+
               (np?' · '+np+' inside PDFs':'')+'</div>';
      hits.forEach(function(h,i){
        var r=h.r, pg=r.k==='pdf'?' <span class="pg">'+esc(r.h)+'</span>':'';
        html+='<a href="'+esc(r.u)+'"'+(r.k==='pdf'?' target="_blank" rel="noopener"':'')+
              ' data-i="'+i+'"><span class="src">'+esc(r.s)+pg+'</span>'+
              (r.k==='page'?'<div class="hd">'+esc(r.h)+'</div>':'')+
              '<div class="sn">'+snippet(r.x,terms)+'</div></a>';
      });
      out.innerHTML=html; box.classList.add('on'); sel=-1;
    });
  }
  var t;
  q.addEventListener('input',function(){
    clearTimeout(t); t=setTimeout(run,140);
    box.classList.toggle('on', q.value.trim().length>=2);
  });
  q.addEventListener('focus',function(){ if(q.value.trim().length>=2) box.classList.add('on'); });
  clr.addEventListener('click',function(){ q.value=''; out.innerHTML='';
    box.classList.remove('on'); q.focus(); });
  q.addEventListener('keydown',function(e){
    var as=out.querySelectorAll('a');
    if(e.key==='Escape'){ box.classList.remove('on'); q.blur(); return; }
    if(!as.length) return;
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){
      e.preventDefault();
      sel += (e.key==='ArrowDown'?1:-1);
      if(sel<0) sel=as.length-1; if(sel>=as.length) sel=0;
      as.forEach(function(a){a.classList.remove('sel');});
      as[sel].classList.add('sel'); as[sel].scrollIntoView({block:'nearest'});
    } else if(e.key==='Enter'){
      e.preventDefault(); (as[sel>=0?sel:0]).click();
    }
  });
  document.addEventListener('click',function(e){ if(!box.contains(e.target)) box.classList.remove('on'); });
  document.addEventListener('keydown',function(e){
    if(e.key==='/' && document.activeElement!==q &&
       !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)){
      e.preventDefault(); q.focus();
    }
  });
})();
"""

pages = sorted(glob.glob('*.html'))
for f in pages:
    h = open(f, encoding='utf-8').read()
    changed = False

    if '.search input{' not in h:
        anchor = '.jump a:hover{background:var(--gold-soft);border-color:var(--gold)}'
        if anchor in h:
            h = h.replace(anchor, anchor + "\n" + CSS.strip(), 1)
        else:
            h = h.replace('</style>', CSS.strip() + "\n</style>", 1)
        changed = True

    if 'id="sitesearch"' not in h:
        m = re.search(r'<main class="wrap">\s*\n', h)
        assert m, f
        h = h[:m.end()] + "\n" + MARKUP + h[m.end():]
        changed = True

    if '/* site search */\n(function(){\n  var box' not in h:
        i = h.rfind('</script>')
        assert i > 0, f
        h = h[:i] + JS + h[i:]
        changed = True

    if changed:
        open(f, 'w', encoding='utf-8').write(h)
    print(('updated ' if changed else 'unchanged ') + f)
