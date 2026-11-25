/* ================= Hàng đợi lệnh in ================= */
const STATUS_TXT={cho_in:'Chờ in',dang_in:'Đang in',da_gui:'Đã gửi máy in',da_ra_giay:'Đã ra giấy',loi:'Lỗi'};
const ACTIVE=new Set(['cho_in','dang_in','da_gui']);
function isPrinter(){try{const v=localStorage.getItem('isPrinter');if(v!==null)return v==='1';}catch{}return !matchMedia('(pointer:coarse)').matches;}
function setPrinter(v){try{localStorage.setItem('isPrinter',v?'1':'0');}catch{}refresh();}

const Jobs={list:[],mode:'server',seen:null,
  loadLocal(){try{return JSON.parse(sessionStorage.getItem('jobs')||'[]');}catch{return[];}},
  saveLocal(){try{sessionStorage.setItem('jobs',JSON.stringify(this.list));}catch{}},
  async refresh(){
    try{this.list=await api('/api/jobs');this.mode='server';}
    catch{this.mode='local';this.list=this.loadLocal();}
    onJobsChanged();
  },
  async create(data,status='cho_in'){
    const body={bks:data.bks||'',xe:[data.nhan_hieu,data.so_loai].filter(Boolean).join(' '),chu:data.ho_ten||'',snapshot:data,status};
    if(this.mode==='server'){try{const j=await api('/api/jobs',{method:'POST',body:JSON.stringify(body)});await this.refresh();return j;}catch{this.mode='local';this.list=this.loadLocal();}}
    const now=Date.now()/1000;const j={id:'L'+Math.round(now*1000),bks:body.bks,xe:body.xe,chu:body.chu,status,created:now,updated:now,lan:status==='dang_in'?1:0,snapshot:data};
    this.list.unshift(j);this.saveLocal();onJobsChanged();return j;
  },
  async snapshot(id){
    if(this.mode==='server'&&!id.startsWith('L'))return api(`/api/jobs/${id}/snapshot`);
    return this.list.find(j=>j.id===id)?.snapshot||{};
  },
  async setStatus(id,status){
    if(this.mode==='server'&&!id.startsWith('L')){try{await api('/api/jobs/'+id,{method:'PATCH',body:JSON.stringify({status})});await this.refresh();return;}catch{}}
    const j=this.list.find(x=>x.id===id);if(j){j.status=status;j.updated=Date.now()/1000;if(status==='dang_in')j.lan++;this.saveLocal();}onJobsChanged();
  },
  async remove(id){
    if(this.mode==='server'&&!id.startsWith('L')){try{await api('/api/jobs/'+id,{method:'DELETE'});await this.refresh();return;}catch{}}
    this.list=this.list.filter(j=>j.id!==id);this.saveLocal();onJobsChanged();
  }};

function onJobsChanged(){
  const active=Jobs.list.filter(j=>ACTIVE.has(j.status)).length;
  $('#qCount').textContent=Jobs.list.length;
  $('#btnQueue').classList.toggle('busy',active>0);
  $('#qCount').hidden=!Jobs.list.length;
  renderQueue();
  // Máy in nhận lệnh mới từ thiết bị khác → tự mở ngăn để nhân viên thấy
  const ids=new Set(Jobs.list.map(j=>j.id));
  if(Jobs.seen){const fresh=Jobs.list.filter(j=>!Jobs.seen.has(j.id)&&j.status==='cho_in');
    if(fresh.length&&isPrinter()&&!currentPrint){openQueue();toast(`Có lệnh in mới: xe ${fresh[0].bks||'(chưa có biển số)'}`);}}
  Jobs.seen=ids;
}
const hhmm=t=>{const d=new Date(t*1000);return `${pad(d.getHours())}:${pad(d.getMinutes())}`;};
function renderQueue(){
  const el=$('#jobList');
  if(!Jobs.list.length){el.innerHTML='<div class="empty"><b>Chưa có lệnh in nào</b><br>Khi bạn bấm In, lệnh sẽ hiện ở đây.</div>';return;}
  el.innerHTML=Jobs.list.map(j=>{
    let act='';
    if(j.status==='cho_in')act=(isPrinter()?`<button class="btn primary sm" data-j="print" data-id="${j.id}">In ngay</button>`:'<span class="hint" style="margin:0">Đang chờ máy tính in</span>')+`<button class="btn link sm" data-j="del" data-id="${j.id}">Xóa</button>`;
    else if(j.status==='dang_in')act=`<span class="hint" style="margin:0">Đang gửi tới máy in…</span><button class="btn secondary sm" data-j="sent" data-id="${j.id}">Đã gửi xong</button><button class="btn danger sm" data-j="cancel" data-id="${j.id}">Huỷ lệnh in</button>`;
    else if(j.status==='da_gui')act=`<button class="btn primary sm" data-j="done" data-id="${j.id}">Đã ra giấy</button><button class="btn danger sm" data-j="fail" data-id="${j.id}">Giấy không ra</button>`;
    else if(j.status==='da_ra_giay')act=(isPrinter()?`<button class="btn secondary sm" data-j="print" data-id="${j.id}">In lại</button>`:'')+`<button class="btn link sm" data-j="del" data-id="${j.id}">Xóa</button>`;
    else if(j.status==='loi')act=(isPrinter()?`<button class="btn primary sm" data-j="print" data-id="${j.id}">In lại</button>`:'')+`<button class="btn link sm" data-j="del" data-id="${j.id}">Xóa</button>`;
    const sub=hhmm(j.created)+(j.lan>1?` · đã in ${j.lan} lần`:'');
    return `<div class="job"><div class="jwho"><b>${esc(j.bks||'Chưa có biển số')}</b><small>${sub}</small></div><span class="jchu">${esc(j.chu||'')}${j.xe?`<small>${esc(j.xe)}</small>`:''}</span><span class="badge ${j.status}">${STATUS_TXT[j.status]}</span>
      <div class="jact">${act}</div>${j.status==='loi'&&j.note?`<p class="jerr">${esc(j.note)}</p>`:''}</div>`;}).join('');
}
document.addEventListener('click',e=>{const im=e.target.closest('.pshot img');if(im)im.classList.toggle('big');});   // chạm ảnh đối chiếu để phóng to / thu nhỏ
$('#jobList').addEventListener('click',async e=>{
  const b=e.target.closest('[data-j]');if(!b)return;const id=b.dataset.id,a=b.dataset.j;
  if(a==='print')printJob(id);
  else if(a==='sent')Jobs.setStatus(id,'da_gui');
  else if(a==='cancel'){try{await fetch(`/api/jobs/${id}/cancel`,{method:'POST'});}catch(e){}toast('Đang huỷ lệnh in…');setTimeout(()=>Jobs.refresh(),1500);}
  else if(a==='done')Jobs.setStatus(id,'da_ra_giay');
  else if(a==='fail')Jobs.setStatus(id,'loi');
  else if(a==='del')Jobs.remove(id);
});
function openQueue(){if(!$('#hdv').hidden){$('#hdv').hidden=true;document.body.style.overflow='';}$('#scrim').hidden=false;$('#drawer').hidden=false;$('#chkPrinter').checked=isPrinter();Jobs.refresh();setTab('btnQueue');}
function closeQueue(){if($('#drawer').hidden)return;$('#scrim').hidden=true;$('#drawer').hidden=true;setTab('tabHome');}
$('#tabHome').onclick=()=>{closeQueue();window.scrollTo({top:0,behavior:'smooth'});};
$('#btnPrn2').onclick=()=>$('#btnPrn').click();
(function hdrQr(n){
  if(!matchMedia('(min-width:1000px)').matches)return;
  if(!hdrQr.w){hdrQr.w=1;document.addEventListener('visibilitychange',()=>{if(!document.hidden)hdrQr(0);});setInterval(()=>hdrQr(0),60000);}   // link tunnel đổi thì mã QR tự cập nhật, khỏi quét nhầm link cũ
  fetch('/api/links').then(r=>r.json()).then(d=>{
    const it=d.items.find(i=>i.url.startsWith('https'));if(!it){setTimeout(()=>hdrQr(n+1),5000);return;}   // chỉ hiện link https (camera)
    $('#hdrQrImg').src=it.qr;$('#hdrQrBig').src=it.qr;$('#hdrQrUrl').textContent=it.url.replace(/^https?:\/\//,'');$('#hdrQr').hidden=false;$('#sbQrImg').src=it.qr;$('#sbQrUrl').textContent=it.url.replace(/^https?:\/\//,'');$('#sbQr').hidden=false;if(typeof fillQrCard==='function')fillQrCard(it);
  }).catch(()=>{if(n<5)setTimeout(()=>hdrQr(n+1),4000);});
})(0);
$('#hdrQr').onclick=$('#sbQr').onclick=()=>$('#tabLink').click();
$('#tabLink').onclick=async()=>{
  $('#linkDlg').hidden=false;$('#linkBody').innerHTML='<p class="lnote">Đang lấy địa chỉ…</p>';
  try{const d=await api('/api/links');d.items=d.items.filter(i=>i.url.startsWith('https'));   // chỉ hiện link https

    $('#linkBody').innerHTML=d.items.length?d.items.map(i=>`<figure class="lk"><img alt="Mã QR ${esc(i.label)}" src="${i.qr}"><figcaption><b>${esc(i.label)}</b><span>${esc(i.url)}</span><small>${esc(i.note)}</small></figcaption></figure>`).join(''):'<p class="lnote">Chưa có địa chỉ để chia sẻ. Hãy chạy máy chủ bằng run.sh / run.cmd.</p>';
    if(!d.items.some(i=>i.url.startsWith('https'))){$('#linkBody').insertAdjacentHTML('beforeend','<p class="lnote"><b>Link https (dùng được camera) chưa có:</b> đang tạo hoặc Cloudflare đang bận — tự thử lại, chờ một lát…</p>');setTimeout(()=>{if(!$('#linkDlg').hidden)$('#tabLink').onclick();},6000);}
  }catch(e){$('#linkBody').innerHTML='<p class="lnote">Không lấy được địa chỉ.</p>';}
};
$('#linkX').onclick=()=>{$('#linkDlg').hidden=true;};$('#linkDlg').addEventListener('click',e=>{if(e.target.id==='linkDlg')$('#linkDlg').hidden=true;});
$('#btnQueue').onclick=openQueue;$('#btnCloseQ').onclick=closeQueue;$('#scrim').onclick=closeQueue;
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeQueue();}});
$('#chkPrinter').onchange=e=>{setPrinter(e.target.checked);renderQueue();};

