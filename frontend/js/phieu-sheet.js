/* ================= Tờ hợp đồng A5 ================= */
function renderSheet(get,preview){
  const fl=(k,cls)=>{const v=get(k);return `<span class="fl ${cls||''} ${(!v&&preview)?'miss':''}">${v?`<span class="v">${esc(v)}</span>`:''}</span>`;};
  const raw=(txt,cls)=>`<span class="fl ${cls||''} ${(!txt&&preview)?'miss':''}">${txt?`<span class="v">${esc(txt)}</span>`:''}</span>`;
  const part=(s,i)=>(s||'').split('/')[i]||'';
  const dmy=(s)=>`${raw(part(s,0),'dot s')} tháng ${raw(part(s,1),'dot s')} năm ${raw(part(s,2),'dot y')}`;
  const n=+get('so_tien')||0,d=+get('so_ngay')||0,st=parseD(get('tu_ngay'));
  const den=st&&d?fmtD(new Date(st.getTime()+d*86400000)):'';
  const l1=[(get('nhan_hieu')||get('so_loai'))&&`Xe ${[get('nhan_hieu'),get('so_loai')].filter(Boolean).join(' ')}`,get('mau')&&`màu ${get('mau')}`,get('bks')&&`BKS ${get('bks')}`].filter(Boolean).join(', ');
  const l2=[get('so_khung')&&`Số khung: ${get('so_khung')}`,get('so_may')&&`Số máy: ${get('so_may')}`].filter(Boolean).join(' — ');
  const nl=get('ngay_lap')||today();
  const dt=get('dt_cua_hang');
  return `<div class="top1"><span class="pre">${dt?`ĐT: <span class="v" style="font-size:8pt">${esc(dt)}</span>`:''}</span><span></span></div>
  <div class="top2"><div class="mp pre">${get('ma_phieu')?`<span class="v" style="font-size:15pt">${esc(get('ma_phieu'))}</span>`:''}</div>
    <div class="ttl"><h3>HỢP ĐỒNG CẦM ĐỒ</h3><div class="sub">( Kiêm Phiếu Chi Tiền )</div></div></div>
  <div class="r"><span class="lb">Họ và tên ông ( bà ):</span>${fl('ho_ten')}<span class="right">Đại diện cầm đồ</span></div>
  <div class="r"><span class="lb">Địa chỉ:</span>${fl('dia_chi')}</div>
  <div class="r"><span class="lb">Cmt số ( hoặc giấy tờ tùy thân khác ):</span>${fl('cccd')}</div>
  <div class="r"><span class="lb">Cấp ngày</span>${dmy(get('ngay_cap'))}<span class="lb">&nbsp;ĐT:</span>${fl('sdt')}</div>
  <div class="r"><span class="lb">Tôi xin thỏa thuận tự nguyện đặt đồ vật, tài sản kê sau đây:</span></div>
  <div class="r tight">${raw(l1)}</div>
  <div class="r tight">${raw(l2)}</div>
  <div class="r tight">${raw('')}</div>
  <div class="r"><span class="lb">Lệ phí thỏa thuận:</span>${raw(get('le_phi')?money(get('le_phi'))+' đồng':'—')}</div>
  <div class="r"><span class="lb">Tôi đã nhận đủ số tiền mà cửa hàng đã giao</span>${raw('')}</div>
  <div class="r tight"><span class="lb">Số tiền viết bằng chữ:</span>${raw(n>0?words(n):'')}</div>
  <div class="r tight"><span class="lb">Số tiền viết bằng số:</span>${raw(n>0?money(n)+' đồng':'')}</div>
  <div class="r ind"><span class="lb">- Từ ngày</span>${dmy(get('tu_ngay'))}</div>
  <div class="r ind tight"><span class="lb">- Đến ngày</span>${dmy(den)}</div>
  <div class="legal">Hiệu cầm đồ được quyền quản lý, điều động khi cần thiết, khi hết hạn mà không có tiền chuộc lại, tôi đồng ý bán đồ vật cầm, ngang bằng tôi đã nhận của cửa hàng.
    <div class="it">- Cửa hàng có quyền bán ( thu vốn )</div><div class="it">- Lời thì cửa hàng được hưởng.</div><div class="it">- Lỗ thì cửa hàng phải chịu.</div>
    Tôi không hề thắc mắc, khiếu kiện, nhờ cậy ai.<br>
    Số tài sản tôi mang cầm chính là tài sản của tôi. Quyền định đoạt cao nhất là tôi, số tài sản này không tranh chấp hoặc cầm cố bất kỳ cá nhân , tổ chức hoặc ngân hàng tín dụng nào.<br>
    Nếu có điều gì man trá, sai trái tôi xin chịu trách nhiệm trước Pháp luật Nhà nước.</div>
  <div class="r date" style="justify-content:flex-end"><span class="lb">Ngày</span>${raw(part(nl,0),'dot s')} tháng ${raw(part(nl,1),'dot s')} năm ${raw(part(nl,2),'dot y')}</div>
  <div class="sign"><div class="l">Phụ trách cửa hàng</div><div>Người nhận tiền<small>( Ký, ghi rõ họ tên )</small></div></div>`;
}

/* ================= Tóm tắt thiếu / cần xem ================= */
const shortLbl=f=>f.l.replace(/\s*\(.*\)/,'');
function summaryHTML(){
  const miss=missingFields(),chk=checkFields();
  if(!miss.length&&!chk.length)return `<div class="summary ok">${ic('check')} Đã đủ thông tin. Có thể in hợp đồng.</div>`;
  let h='';
  if(miss.length)h+=`<div class="srow bad"><span class="dot"></span><span class="tx"><b>Thiếu ${miss.length} mục</b></span><button type="button" class="sbtn" data-focus="${miss[0].k}">Đến ô thiếu</button></div>`;
  if(chk.length)h+=`<div class="srow warn"><span class="dot"></span><span class="tx"><b>${chk.length} ô cần soát</b> <small>so với giấy tờ</small></span><button type="button" class="sbtn" id="btnAllOk">Đều đúng</button></div>`;
  return h;
}
document.addEventListener('click',e=>{
  const c=e.target.closest('[data-focus]');
  if(c){const i=document.querySelector(`#phieu [data-k="${c.dataset.focus}"],#phieu [data-dk="${c.dataset.focus}"]`);if(i){i.scrollIntoView({block:'center',behavior:'smooth'});setTimeout(()=>i.focus(),250);}}
  if(e.target.closest('#btnAllOk')){checkFields().forEach(f=>{state[f.k].status='ok';state[f.k].note='';});refresh();}
});

const DRAFT='hs_draft_v1';
let wstep=1;
function saveDraft(){try{sessionStorage.setItem(DRAFT,JSON.stringify({state,step:wstep}));}catch(e){}}
function loadDraft(){try{const d=JSON.parse(sessionStorage.getItem(DRAFT)||'null');if(d&&d.state){Object.assign(state,d.state);return d;}}catch(e){}return null;}
function refresh(){
  saveDraft();
  $('#sum').innerHTML=summaryHTML();paintStatus();paintReview();paintSheets();
  const miss=missingFields();
  const b=$('#btnPrint');b.disabled=miss.length>0;
  const why=miss.map(f=>{const v=val(f.k),sh=f.l.replace(/\s*\(.*\)/,'');return v?`${sh}: ${validate(f.k,v).note}`:`${sh} chưa nhập`;});
  const pn=$('#printerNote');pn.classList.toggle('blocked',miss.length>0);
  b.textContent=miss.length?'Chưa thể tạo hồ sơ':'Tạo hồ sơ & in';
  if(miss.length){pn.textContent='Chưa in được vì: '+why.slice(0,3).join('; ')+(why.length>3?` … và ${why.length-3} mục khác`:'')+'.';pn.dataset.focus=miss[0].k;return;}
  delete pn.dataset.focus;
  pn.textContent=(isPrinter()?(PS.overlay?'Đặt giấy mẫu vào máy in trước. Chỉ in phần thông tin điền vào.':'Sẽ mở hộp thoại in, chọn máy in khổ A5.'):'Máy này không nối máy in: lệnh in sẽ gửi sang máy tính trong tiệm, nhân viên bấm In ở đó.')+' Hồ sơ được tạo ngay khi bấm. In lỗi thì hồ sơ vẫn còn, in lại ở mục Lệnh in.';
}

