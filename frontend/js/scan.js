const ANDROID=/Android/i.test(navigator.userAgent);
function openExternal(){
  const u=location.href.replace(/^https?:\/\//,'');
  if(ANDROID)location.href='intent://'+u+'#Intent;scheme=https;action=android.intent.action.VIEW;end';
  else location.href='x-safari-https://'+u;                 // iOS: không đảm bảo, nếu bị chặn thì dùng nút Chép link
}
if(IN_APP){$('#inapp').hidden=false;$('#inappOpen').onclick=openExternal;
  if(ANDROID&&!sessionStorage.getItem('tried_ext')){sessionStorage.setItem('tried_ext','1');setTimeout(openExternal,300);}
  $('#inappX').onclick=()=>{$('#inapp').hidden=true;};
  $('#inappCopy').onclick=async()=>{try{await navigator.clipboard.writeText(location.href);toast('Đã chép link. Dán vào Safari hoặc Chrome.');}catch(e){prompt('Chép link này:',location.href);}};}
$('#camShot').onclick=()=>snap('manual');$('#camTorch').onclick=toggleTorch;$('#camClose').onclick=closeCam;
addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#cam').hidden)closeCam();});
function scanMsg(cls,html,spin){$('#scanStatus').innerHTML=html?`<div class="banner ${cls}">${spin?'<div class="spinner" aria-hidden="true"></div>':''}<div>${html}</div></div>`:'';}
let scanning=false;
/* Dữ liệu đã đọc + soát ngay trong camera (cả 2 giấy tờ) → điền thẳng, không đọc lại trên máy chủ */
function fillFromCam(){
  const ks=['cccd_back','cavet'];if(!ks.every(k=>camFix[k]&&camFix[k].cam&&camFix[k].all))return false;
  if(!ks.every(k=>Object.keys(camFix[k].all).length)){tr('fallback',{why:'camera_chua_doc_duoc',cccd_back:Object.keys(camFix.cccd_back.all).length,cavet:Object.keys(camFix.cavet.all).length});return false;}   // camera chưa đọc được ô nào của 1 giấy: để máy chủ đọc ảnh vừa chụp
  if(camFix.cccd_front&&camFix.cccd_front.all)ks.push('cccd_front');
  const put=(k,v,st)=>{if(!v)return;if(k==='mau')v=fixMau(v);const vv=validate(k,v),bad=vv&&vv.status!=='ok';
    state[k]={value:v,status:bad?vv.status:(st==='ok'?'ok':'check'),note:bad?vv.note:(st==='ok'?'':'Kiểm tra lại với giấy tờ')};};
  for(const k of ks){for(const[key,o]of Object.entries(camFix[k].all)){
    if(key==='nhan_hieu'){const[a,...b]=o.v.split(/\s+-\s+/);put('nhan_hieu',a,o.st);if(b.length)put('so_loai',b.join(' - '),o.st);}else put(key,o.v,o.st);}
    for(const key of PEEK_EXPECT[k]){const ex=key==='nhan_hieu'?['nhan_hieu','so_loai']:[key];
      ex.forEach(x=>{if(!state[x]||!state[x].value)state[x]={value:'',status:FIELDS.find(f=>f.k===x)?.req?'missing':'ok',note:'Không đọc được — vui lòng nhập'};});}}
  for(const k in crops)delete crops[k];
  applyCamFix();renderReview();dupCheck(true);refresh();paintRvImgs();
  const bad=ks.reduce((n,k)=>n+Object.values(camFix[k].all).filter(o=>o.st!=='ok').length,0);
  tr('fill',{cards:ks.length,review:bad});
  toast(bad?`Có ${bad} ô cần bạn xem lại.`:'Đã đọc xong. Vẫn nên đối chiếu lại với giấy tờ.');
  return true;
}
async function scanNow(){
  if(scanning)return;
  if(fillFromCam())return;
  scanning=true;
  while(stacking)await new Promise(r=>setTimeout(r,80));
  const fd=new FormData();for(const[k,f]of Object.entries(files))fd.append(k,f);
  document.body.classList.add('scanning');paintReview();scanMsg('info','<b>Đang đọc giấy tờ…</b><br>Khoảng 5–10 giây, vui lòng chờ.',true);
  try{
    const r=await fetch('/api/scan',{method:'POST',body:fd});if(!r.ok)throw new Error('Máy chủ trả lỗi '+r.status);
    const data=await r.json();
    for(const[k,o0]of Object.entries(data.fields)){
      let o=(k==='mau'&&o0.value)?{...o0,value:fixMau(o0.value)}:o0;
      if(!o.value&&liveAcc[k]&&liveAcc[k].value)o={value:liveAcc[k].value,status:'check',note:'Đọc từ camera lúc ngắm — kiểm tra lại với giấy tờ'};   // ảnh chụp cuối không đọc được nhưng lúc ngắm đã đọc được
      if(!o.value&&state[k]?.value)continue;
      if(o.crop)crops[k]=o.crop;else delete crops[k];
      const vv=o.value?validate(k,o.value):null;
      state[k]={value:o.value||'',status:(vv&&vv.status!=='ok')?vv.status:(o.value?o.status:(FIELDS.find(f=>f.k===k)?.req?'missing':'ok')),note:(vv&&vv.status!=='ok')?vv.note:(o.note||(o.value?'':'Không đọc được — vui lòng nhập'))};
    }
    applyCamFix();scanMsg('','');document.body.classList.remove('scanning');renderReview();dupCheck(true);refresh();
    const bad=Object.values(data.fields).filter(o=>o.status!=='ok'||!o.value).length;
    toast(bad?`Đã đọc xong. Có ${bad} ô cần bạn xem lại hoặc nhập.`:'Đã đọc xong. Vẫn nên đối chiếu lại với giấy tờ.');
    (data.warnings||[]).forEach(w=>toast(w));
  }catch(e){scanMsg('err',`<b>Chưa đọc được giấy tờ.</b><br>${esc(e.message)}. Bạn vẫn có thể bấm “Nhập tay”.`);}
  scanning=false;document.body.classList.remove('scanning');paintRvImgs();
}

let toastT;function toast(m){const t=$('#toast');t.textContent=m;t.hidden=false;clearTimeout(toastT);toastT=setTimeout(()=>t.hidden=true,5000);}

