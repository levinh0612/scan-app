/* ================= In ================= */
let currentPrint=null;
function snapshotNow(){const o={};FIELDS.filter(f=>f.k).forEach(f=>o[f.k]=val(f.k));o.ngay_lap=today();return o;}

let sending=false;
/* Tạo hồ sơ rồi mới in. Hồ sơ là việc chính: lưu lỗi thì KHÔNG in (tránh có giấy mà không có hồ sơ); in lỗi thì hồ sơ vẫn còn, in lại ở Lệnh in. */
async function sendPrint(snap){       // → {st:'ok'|'wait'|'err'|'dlg', msg}
  let job;
  try{job=await Jobs.create(snap,'cho_in');}catch(e){return {st:'err',msg:'Chưa tạo được lệnh in.'};}
  if(!isPrinter())return {st:'wait',msg:'Đã gửi sang máy tính ở tiệm, nhân viên bấm In ở đó.'};
  let ok;try{ok=await printJob(job.id);}catch(e){ok=false;}
  if(currentPrint)return {st:'dlg'};      // in bằng hộp thoại trình duyệt: kết quả hỏi sau khi in xong
  if(!ok)return {st:'err',msg:'Chưa gửi được ra máy in. Mở Lệnh in để in lại.'};
  const j=Jobs.list.find(x=>x.id===job.id);
  if(j&&j.status==='loi')return {st:'err',msg:'Máy in báo lỗi'+(j.note?': '+j.note:'')+'. Mở Lệnh in để in lại.'};
  return {st:'ok',msg:'Đã gửi ra máy in. Nhớ kiểm tra giấy đã ra chưa.'};
}
$('#btnPrint').onclick=async()=>{
  if(sending||missingFields().length)return;               // chốt chặn thứ 2 + chống bấm đúp
  sending=true;$('#btnPrint').disabled=true;
  try{
    const snap=snapshotNow();
    const saved=await saveContract(snap);
    if(!saved){showSaveFail();return;}                     // chưa có hồ sơ thì chưa in
    const res=await sendPrint(snap);
    if(res.st!=='dlg')showCreated(saved,snap,res);
  }finally{sending=false;refresh();}
};
function showSaveFail(){
  openModal(`<div class="big bad" aria-hidden="true">!</div><h2>Chưa tạo được hồ sơ</h2>
    <p>Hồ sơ <b>chưa được lưu</b> nên app <b>chưa in</b>. Dữ liệu bạn nhập vẫn còn nguyên.</p>
    <div class="stack"><button class="btn primary" id="m-retry">Thử lại</button><button class="btn link" id="m-x">Đóng</button></div>`);
  $('#m-retry').onclick=()=>{closeModal();$('#btnPrint').click();};$('#m-x').onclick=closeModal;
}
/* Kết quả gồm 2 việc riêng: hồ sơ và lệnh in */
function showCreated(saved,snap,res){
  const c=saved.contract,ma=esc(c.ma),bad=res.st==='err';
  resetAll();
  openModal(`<div class="big ${bad?'ask':'ok'}" aria-hidden="true">${bad?'!':ic('check')}</div><h2>${saved.duplicate?`Hồ sơ ${ma} đã có sẵn`:`Đã tạo hồ sơ ${ma}`}</h2>
    <p>Xe <b>${esc(snap.bks)}</b> · chủ xe <b>${esc(snap.ho_ten)}</b>.</p>
    <ul class="rs"><li class="ok"><b>Hồ sơ</b><span>${saved.duplicate?'Đã có trong kho':'Đã lưu, hạn '+esc(c.den_ngay_vn)}</span></li>
    <li class="${bad?'bad':'ok'}"><b>Lệnh in</b><span>${esc(res.msg)}</span></li></ul>
    <div class="stack">${bad?'<button class="btn primary" id="m-again">In lại</button>':''}<button class="btn ${bad?'secondary':'primary'}" id="m-new">Tạo hồ sơ mới</button><button class="btn link" id="m-view">Xem hồ sơ</button><button class="btn link" id="m-q">Xem lệnh in</button></div>`);
  $('#m-new').onclick=closeModal;
  $('#m-view').onclick=()=>{closeModal();hdShow(c.id);};
  $('#m-q').onclick=()=>{closeModal();openQueue();};
  if(bad)$('#m-again').onclick=async()=>{const b=$('#m-again');b.disabled=true;const r=await sendPrint(snap);if(r.st==='dlg')closeModal();else showCreated(saved,snap,r);};
}
async function printJob(id){
  const snap=await Jobs.snapshot(id);
  if(!snap||!Object.keys(snap).length){toast('Lệnh in này đã hết hạn, hãy tạo lại.');return;}
  // In từ máy chủ (không hộp thoại). Máy chủ tự cập nhật trạng thái: Đang in → Đã gửi máy in / Lỗi + lý do.
  if(Jobs.mode==='server'&&!id.startsWith('L')){
    try{await api(`/api/jobs/${id}/print`,{method:'POST'});await Jobs.refresh();return true;}
    catch{toast('Không gọi được máy chủ in. Kiểm tra máy tính ở tiệm đang chạy rồi bấm In lại.');return false;}
  }
  toast('Chưa kết nối máy chủ in, chưa thể in. Lệnh in được giữ lại trong Lệnh in.');
  return false;
}
// Trình duyệt không cho biết giấy đã ra thật hay chưa; afterprint chạy khi hộp thoại in đóng lại.
window.addEventListener('afterprint',async()=>{
  if(!currentPrint)return;const {id,snap}=currentPrint;currentPrint=null;
  await Jobs.setStatus(id,'da_gui');showAfterPrint(id,snap);
});
function openModal(html){$('#modalBox').innerHTML=html;$('#modal').hidden=false;const f=$('#modalBox button');f&&f.focus();}
function closeModal(){$('#modal').hidden=true;}
function showAfterPrint(id,snap){
  openModal(`<div class="big ask" aria-hidden="true">!</div><h2>Đã gửi lệnh in</h2>
    <p>Xe <b>${esc(snap.bks)}</b> · chủ xe <b>${esc(snap.ho_ten)}</b>.<br>Hãy kiểm tra giấy đã ra chưa.</p>
    <div class="stack"><button class="btn primary" id="m-ok">Đã ra giấy</button><button class="btn danger" id="m-fail">Giấy không ra / bị lỗi</button><button class="btn link" id="m-later">Xem sau</button></div>`);
  $('#m-ok').onclick=async()=>{await Jobs.setStatus(id,'da_ra_giay');showDone(snap);};
  $('#m-fail').onclick=async()=>{await Jobs.setStatus(id,'loi');closeModal();openQueue();};
  $('#m-later').onclick=()=>{closeModal();openQueue();};
}
function showDone(snap){
  openModal(`<div class="big ok" aria-hidden="true">${ic('check')}</div><h2>Hoàn thành hồ sơ</h2>
    <p>Hồ sơ của xe <b>${esc(snap.bks)}</b> (${esc([snap.nhan_hieu,snap.so_loai].filter(Boolean).join(' - '))})<br>và chủ xe: <b>${esc(snap.ho_ten)}</b></p>
    <div class="stack"><button class="btn primary" id="m-new">Làm hồ sơ mới</button><button class="btn link" id="m-back">Quay lại hồ sơ này</button></div>`);
  $('#m-new').onclick=()=>{closeModal();resetAll();};
  $('#m-back').onclick=closeModal;
}

