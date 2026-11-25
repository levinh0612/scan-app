/* ================= Làm mới ================= */
function resetAll(){
  Object.keys(camFix).forEach(k=>delete camFix[k]);
  try{sessionStorage.removeItem(DRAFT);}catch(e){}
  for(const k in state)delete state[k];for(const k in files)delete files[k];cccdQR=false;peekAcc={};liveAcc={};
  for(const k in crops)delete crops[k];
  rvManual=false;scanMsg('','');initState();goStep(2);
}
function initState(){
  state.tu_ngay={value:today(),status:'ok',note:'Mặc định là hôm nay. Sửa nếu cần.',edited:true};
  state.so_ngay={value:String((typeof DEF!=='undefined'&&DEF&&DEF.so_ngay_ky)||30),status:'ok',note:'Mặc định theo Cài đặt, sửa nếu khác.'};
  if(typeof DEF!=='undefined'&&DEF&&+DEF.le_phi_ky>0)state.le_phi={value:String(DEF.le_phi_ky),status:'ok',note:'Mặc định theo Cài đặt.'};
}

function goStep(n,quiet){
  wstep=n;document.body.dataset.w=n;
  document.querySelectorAll('#wz button').forEach(b=>{const k=+b.dataset.go;b.classList.toggle('on',k===n);b.classList.toggle('done',k<n);if(k===n)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');});
  if(n!==3)wantPrint=false;
  if(n===2){renderReview();dupCheck(true);}
  if(n===3)renderPhieu();
  refresh();
  if(!quiet)window.scrollTo({top:0,behavior:'smooth'});
  if(n===3)setTimeout(fitPhieu,0);
  if(n===3&&wantPrint){wantPrint=false;setTimeout(()=>{const b=$('#btnPrint');if(!b.disabled)b.click();},500);}   // "In hợp đồng" ở bước 2: qua đủ cổng kiểm tra rồi mới in
  if(n===2&&!quiet){const f=['sdt','so_tien'].map(k=>document.querySelector(`#rvBody [data-k="${k}"]`)).find(i=>i&&!i.value);if(f)setTimeout(()=>f.focus({preventScroll:true}),350);}
}
function gateToPrint(){
  const miss=missingFields(),chk=checkFields();
  if(miss.length){
    const i=document.querySelector(`#rvBody [data-k="${miss[0].k}"]`);if(i){i.scrollIntoView({block:'center',behavior:'smooth'});setTimeout(()=>i.focus({preventScroll:true}),300);}
    toast(`Còn ${miss.length} mục chưa hợp lệ: ${miss.slice(0,3).map(shortLbl).join(', ')}${miss.length>3?'…':''}`);return;
  }
  if(chk.length&&POLICY.confirmWarnings){
    openModal(`<div class="big ask" aria-hidden="true">!</div><h2>${chk.length} mục cần soát</h2>
      <p>Máy chưa chắc chắn. Nếu đã so với giấy tờ và đúng rồi thì giữ nguyên.</p>
      <ul class="wlist">${chk.map(f=>`<li><b>${esc(RV_LBL[f.k]||f.l)}: ${esc(val(f.k))}</b><span>${esc(state[f.k].note)}</span></li>`).join('')}</ul>
      <div class="stack"><button class="btn primary" id="m-keep">Giữ nguyên, xem phiếu</button><button class="btn link" id="m-back2">Quay lại soát</button></div>`);
    $('#m-keep').onclick=()=>{checkFields().forEach(f=>{state[f.k].status='ok';state[f.k].note='';});closeModal();askDup(()=>goStep(3));};
    $('#m-back2').onclick=()=>{closeModal();const i=document.querySelector(`#rvBody [data-k="${chk[0].k}"]`);if(i)i.scrollIntoView({block:'center',behavior:'smooth'});};
    return;
  }
  askDup(()=>goStep(3));
}
function askDup(next){
  const hi=dups.filter(w=>w.level==='high');
  if(!hi.length)return next();
  const hard=hi.filter(w=>/_active$/.test(w.kind));   // trùng đúng xe đang cầm → chặn hẳn
  if(hard.length){
    openModal(`<div class="big ask" aria-hidden="true">!</div><h2>Xe này đang cầm, chưa chuộc</h2><ul class="wlist">${dupLines(hard).map(m=>`<li><b>${esc(m)}</b></li>`).join('')}</ul><p>Không thể lập hợp đồng mới cho xe đang cầm. Nếu máy đọc sai thì sửa lại ô tương ứng (ô được tô đỏ).</p><div class="stack"><button class="btn primary" id="m-fix" type="button">Quay lại sửa</button></div>`);
    $('#m-fix').onclick=closeModal;return;
  }
  openModal(`<div class="big ask" aria-hidden="true">!</div><h2>Xe này đã có trong hệ thống</h2><ul class="wlist">${dupLines(hi).map(m=>`<li><b>${esc(m)}</b></li>`).join('')}</ul><p>Nếu OCR đọc sai thì sửa lại ô tương ứng. Nếu đúng là xe đó thì không nên lập hợp đồng mới khi chưa chuộc.</p><div class="stack"><button class="btn primary" id="m-fix">Quay lại sửa</button><button class="btn link" id="m-go">Vẫn lập hợp đồng</button></div>`);
  $('#m-fix').onclick=closeModal;$('#m-go').onclick=()=>{closeModal();next();};
}
document.querySelectorAll('#wz button').forEach(b=>b.onclick=()=>{const n=+b.dataset.go;if(n<=wstep)goStep(n);else if(wstep===2)gateToPrint();else goStep(2);});
$('#btnSkip').onclick=()=>{rvManual=true;renderReview();$('#btnSkip').hidden=true;};
let wantPrint=false;
$('#rvRescan').onclick=()=>{
  openModal(`<div class="big ask" aria-hidden="true">!</div><h2>Quét lại từ đầu?</h2><p>Toàn bộ dữ liệu và ảnh đã quét, đã nhập của hồ sơ này sẽ bị xóa.</p>
    <div class="stack"><button class="btn danger" id="m-rs" type="button">Xóa và quét lại</button><button class="btn link" id="m-rc" type="button">Giữ lại</button></div>`);
  $('#m-rc').onclick=closeModal;$('#m-rs').onclick=()=>{closeModal();resetAll();toast('Đã xóa, hãy quét lại.');};
};
$('#rvNext').onclick=()=>{wantPrint=false;gateToPrint();};
document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>goStep(2));


addEventListener('resize',()=>{document.querySelectorAll('#rvBody textarea.ei').forEach(t=>{if(t.offsetParent)autoGrow(t);});});
