/* --- Trang chủ (chỉ điện thoại <1000px): lối tắt, số liệu nhanh, hoạt động gần đây --- */
const isPhone=()=>matchMedia('(max-width:999px)').matches;
const HM_IC={
  scan:'<path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2M4 12h16"/>',
  edit:'<path d="M4 20h4L19 9l-4-4L4 16zM13 7l4 4"/>',
  doc:'<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7"/>',
  prn:'<path d="M7 9V4h10v5M7 17H5a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2M7 14h10v6H7z"/>',
  lock:'<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  go:'<path d="M9 5l7 7-7 7"/>'};
const hmI=n=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${HM_IC[n]}</svg>`;
const hmDraft=()=>typeof state==='object'&&['ho_ten','cccd','bks','so_khung','so_may'].some(k=>state[k]&&state[k].value);

function homePaint(st,recent){
  const el=$('#home');
  const d=new Date(),wd=['Chủ nhật','Thứ hai','Thứ ba','Thứ tư','Thứ năm','Thứ sáu','Thứ bảy'][d.getDay()];
  const row=(go,l,n,c='')=>`<button type="button" class="hmli" data-go="${go}"><span class="${c}">${l}</span><b class="${c}">${n}</b>${hmI('go')}</button>`;
  const sum=st
    ?`<div class="hmgrp">${row('hd','Đang cầm',st.dang_cam)}${st.qua_han?row('hd','Quá hạn',st.qua_han,'bad'):''}${st.sap_han?row('hd','Sắp đến hạn',st.sap_han,'warn'):''}</div>`
    :`<div class="hmgrp"><button type="button" class="hmli" data-go="hd"><span>${hmI('lock')}Nhập mã PIN để xem hợp đồng</span>${hmI('go')}</button></div>`;
  const rows=(recent||[]).map(c=>{const tone=c.hien_thi==='qua_han'?'bad':c.hien_thi==='sap_han'?'warn':'';
    return `<button type="button" class="hmr" data-id="${c.id}"><span class="hmra"><b>${esc(c.ho_ten)||'(chưa có tên)'}</b><small>${esc(c.bks)}</small></span><span class="hmrb">${AU.local?`<b>${money(c.so_tien)}</b>`:''}<small class="${tone}">${esc(hdHanText(c))}</small></span></button>`;}).join('');
  el.innerHTML=`<div class="hmin">
    <header class="hmh"><small>${wd}, ${d.getDate()}/${d.getMonth()+1}</small><h1>Trang chủ</h1></header>
    ${hmDraft()?`<button type="button" class="hmdraft" data-go="scan"><span><b>Hồ sơ đang làm dở</b><small>Bấm để tiếp tục</small></span>${hmI('go')}</button>`:''}
    <button type="button" class="hmbig" data-go="scan">${hmI('scan')}Quét hồ sơ mới</button>
    <div class="hmtwo"><button type="button" class="hms" data-go="manual">${hmI('edit')}Nhập tay</button><button type="button" class="hms prn" id="hmPrnQ" data-go="prn" data-s="unknown"><span class="pdot"></span><span id="hmPrnS">Máy in</span></button></div>
    ${sum}
    ${recent&&recent.length?`<h2 class="hmsec">Gần đây</h2><div class="hmlist">${rows}</div>`:''}</div>`;
  homePrn();
  el.onclick=e=>{const b=e.target.closest('[data-go],[data-id]');if(!b)return;
    if(b.dataset.id){$('#tabHd').click();setTimeout(()=>hdShow(+b.dataset.id),400);return;}
    homeStart(b.dataset.go);};
}
function homePrn(){const q=$('#hmPrnQ');if(!q)return;
  const s=$('#btnPrn').dataset.s||'unknown';q.dataset.s=s;
  $('#hmPrnS').textContent={ready:'Máy in: đã kết nối',printing:'Máy in: đang in',offline:'Máy in: chưa kết nối',error:'Máy in: lỗi',none:'Chưa có máy in'}[s]||'Máy in: đang kiểm tra';}
async function homeShow(){
  if(!isPhone())return;
  document.body.classList.add('onhome');$('#home').hidden=false;setTab('tabHome');window.scrollTo(0,0);
  homePaint(null,[]);
  const st=await hdStatsRefresh();let recent=[];
  if(st&&AU.authed){try{recent=(await api('/api/contracts?q=&status=dang_cam')).items.slice(0,4);}catch(e){}}
  if(document.body.classList.contains('onhome'))homePaint(st,recent);
}
function homeHide(){document.body.classList.remove('onhome');$('#home').hidden=true;}
function homeStart(k){
  if(k==='hd'){$('#tabHd').click();return;}
  if(k==='prn'){$('#btnQueue').click();return;}
  homeHide();window.scrollTo(0,0);
  if(k==='manual'){const b=$('#btnSkip');if(b&&!b.hidden)b.click();}
  else if(k==='scan'){const t=!files.cccd_back?'cccd_back':!files.cavet?'cavet':'';if(t)pickPhoto(t);}   // vào thẳng camera cho giấy tờ còn thiếu
}
$('#tabHome').addEventListener('click',()=>{if(isPhone()){homeHide();window.scrollTo(0,0);}});   // mở app / bấm tab đầu: vào thẳng màn quét, không còn Trang chủ
$('#tabHd').addEventListener('click',homeHide);
$('#tabRp').addEventListener('click',homeHide);
$('#tabSt').addEventListener('click',homeHide);
$('#btnQueue').addEventListener('click',homeHide);
setInterval(()=>{if(!document.hidden&&document.body.classList.contains('onhome'))homePrn();},2000);
