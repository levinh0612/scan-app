/* --- Xác thực: máy chủ trong tiệm vào thẳng, điện thoại phải nhập PIN --- */
const AU={local:false,authed:false,pin_set:false,pin_len:0,locked:0,idle:300,tok:'',t:Date.now()};
try{AU.tok=sessionStorage.getItem('sess')||'';}catch{}
const setTok=t=>{AU.tok=t||'';try{t?sessionStorage.setItem('sess',t):sessionStorage.removeItem('sess');}catch{}};
async function api(path,opt={}){
  const h={'Content-Type':'application/json',...(opt.headers||{})};if(AU.tok)h['X-Session']=AU.tok;
  const r=await fetch(path,{...opt,headers:h});
  if(!r.ok){let m=String(r.status);try{const j=await r.json();if(j&&typeof j.detail==='string')m=j.detail;}catch{}
    const e=new Error(m);e.status=r.status;e.retry=+r.headers.get('Retry-After')||0;
    if(r.status===401&&!AU.local){AU.authed=false;setTok('');}
    throw e;}
  AU.t=Date.now();return r.json();
}
async function authInit(){
  try{const r=await fetch('/api/auth/status',{headers:AU.tok?{'X-Session':AU.tok}:{}});const s=await r.json();
    Object.assign(AU,{local:s.local,authed:s.local||s.authed,pin_set:s.pin_set,pin_len:s.pin_len||0,locked:s.locked_for||0,idle:s.idle||300});
    if(!AU.authed&&AU.tok)setTok('');}catch(e){}
  return AU;
}
async function lockNow(){try{await fetch('/api/auth/logout',{method:'POST',headers:AU.tok?{'X-Session':AU.tok}:{}});}catch{}setTok('');AU.authed=AU.local;if(!AU.local&&!$('#hdv').hidden)hdHome();}
setInterval(()=>{if(!AU.local&&AU.authed&&Date.now()-AU.t>AU.idle*1000)lockNow();},10000);
['click','keydown','touchstart'].forEach(ev=>document.addEventListener(ev,()=>{if(AU.authed)AU.t=Date.now();},{passive:true}));

