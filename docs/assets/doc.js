(function(){
var d=document,$=function(s,r){return (r||d).querySelector(s)},$$=function(s,r){return Array.prototype.slice.call((r||d).querySelectorAll(s))};
var ls={g:function(k){try{return localStorage.getItem(k)}catch(e){return null}},s:function(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
// theme
var t=ls.g('doc-theme');if(t)d.documentElement.dataset.theme=t;
var tb=$('.tbtn');if(tb)tb.onclick=function(){var dark=matchMedia('(prefers-color-scheme:dark)').matches;var cur=d.documentElement.dataset.theme||(dark?'dark':'light');var n=cur==='dark'?'light':'dark';d.documentElement.dataset.theme=n;ls.s('doc-theme',n);if(window.mermaidInit)window.mermaidInit()};
// mobile nav
var mb=$('.top button');if(mb)mb.onclick=function(){d.body.classList.toggle('open')};
var sc=$('.scrim');if(sc)sc.onclick=function(){d.body.classList.remove('open')};
// progress + toc spy
var pg=$('#prog'),hs=$$('article h2'),ta=$$('.toc a');
function onS(){var h=d.documentElement,m=h.scrollHeight-h.clientHeight;pg.style.width=(m>0?h.scrollTop/m*100:0)+'%';
  var cur=null;hs.forEach(function(x){if(x.getBoundingClientRect().top<120)cur=x.id});
  ta.forEach(function(a){a.classList.toggle('on',a.getAttribute('href')==='#'+cur)})}
addEventListener('scroll',onS,{passive:true});onS();
// copy buttons
$$('pre').forEach(function(p){if(p.parentNode.classList.contains('mermaid'))return;var b=d.createElement('button');b.className='cp';b.textContent='Sao chép';b.onclick=function(){navigator.clipboard&&navigator.clipboard.writeText(p.innerText.replace(/Sao chép$/,'').trim());b.textContent='Đã chép ✓';setTimeout(function(){b.textContent='Sao chép'},1400)};p.appendChild(b)});
// checklists
var key='chk:'+location.pathname.split('/').pop();var saved={};try{saved=JSON.parse(ls.g(key)||'{}')}catch(e){}
var boxes=$$('ul.chk input');
if(boxes.length){
  var bar=d.createElement('div');bar.className='chkbar';bar.innerHTML='<b>Tiến độ nghiệm thu</b><div class="bar"><i></i></div><span class="cnt"></span><button>Đặt lại</button>';
  var first=$('ul.chk');first.parentNode.insertBefore(bar,first);
  function upd(){var n=boxes.filter(function(b){return b.checked}).length;$('.bar i',bar).style.width=(n/boxes.length*100)+'%';$('.cnt',bar).textContent=n+' / '+boxes.length;var o={};boxes.forEach(function(b,i){if(b.checked)o[i]=1;b.closest('li').classList.toggle('done',b.checked)});ls.s(key,JSON.stringify(o))}
  boxes.forEach(function(b,i){b.checked=!!saved[i];b.closest('li').onclick=function(e){if(e.target!==b){b.checked=!b.checked}upd()}});
  $('button',bar).onclick=function(){boxes.forEach(function(b){b.checked=false});upd()};upd();
}
})();
