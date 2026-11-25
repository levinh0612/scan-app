/* ================= Quy trình 3 bước ================= */
/* Bước 2: 3 thẻ như màn Quét (CCCD, Cà vẹt) + thẻ Khoản cầm. Đổi thứ tự / nhóm ô tại đây; "den" là ô tự tính. */
const REVIEW_CARDS=[
  {id:'cccd',t:'CCCD · mặt sau',sub:'Chụp bằng camera, app tự điền các ô',hint:'Mặt sau, có mã QR',img:['cccd_back','cccd_front'],keys:['ho_ten','cccd','ngay_cap','dia_chi']},
  {id:'cavet',t:'Cà vẹt xe',sub:'Chụp bằng camera, app tự điền các ô',hint:'Trang có biển số và số khung',img:['cavet'],keys:['bks','nhan_hieu','so_loai','mau','so_may','so_khung']},
  {id:'cam',t:'Khoản cầm',sub:'',keys:['sdt','so_tien','le_phi','so_ngay','tu_ngay','den']},
];
const RV_OPT={sdt:{mode:'tel',ph:'vd 0905123456'},so_tien:{mode:'numeric',ph:'vd 5.000.000'},cccd:{mode:'numeric',max:12},ngay_cap:{mode:'numeric',max:10,ph:'ngày/tháng/năm'},
  tu_ngay:{mode:'numeric',max:10,ph:'ngày/tháng/năm'},so_ngay:{mode:'numeric'},le_phi:{mode:'numeric',ph:'không bắt buộc'},nhan_hieu:{ph:'hãng'},so_loai:{ph:'loại / model'},mau:{ph:'Bấm để chọn màu'}};
const RV_LBL={sdt:'Số điện thoại',so_tien:'Số tiền cầm',ho_ten:'Họ và tên',cccd:'Số CCCD',ngay_cap:'Ngày cấp',dia_chi:'Địa chỉ',bks:'Biển số',nhan_hieu:'Nhãn hiệu',so_loai:'Số loại (model)',so_khung:'Số khung',so_may:'Số máy',mau:'Màu sơn',tu_ngay:'Từ ngày',so_ngay:'Số ngày cầm',le_phi:'Lệ phí thỏa thuận'};
const rvBase=k=>`<div class="rv" data-row="${k}"><label>${RV_LBL[k]||LBL[k]||k}</label>${k==='dia_chi'?txa(k):inp(k,RV_OPT[k]||{})}<div class="rvh" data-h="${k}" hidden></div><div class="rvm" data-m="${k}"></div></div>`;
/* Từ ngày ──[30 ngày]── Đến ngày: một khối thời gian; "so_ngay" và "den" nằm trong khối của "tu_ngay" */
const rvTimeline=()=>`<div class="tl">${rvBase('tu_ngay')}
  <div class="rv tlm" data-row="so_ngay"><label>${RV_LBL.so_ngay}</label><span class="pill">${inp('so_ngay',RV_OPT.so_ngay)}<span>ngày</span></span><div class="rvh" data-h="so_ngay" hidden></div><div class="rvm" data-m="so_ngay"></div></div>
  <div class="rcalc"><label>Đến ngày</label><span class="chip tu">Tự tính</span><input id="rvDen" class="ei" inputmode="numeric" maxlength="10" placeholder="ngày/tháng/năm" autocomplete="off"></div></div>`;
const rvRow=k=>k==='tu_ngay'?rvTimeline():(k==='so_ngay'||k==='den')?'':rvBase(k);
function renderReview(){
  $('#rvBody').innerHTML=REVIEW_CARDS.map(c=>`<section class="rcd" data-card="${c.id}"${c.img?` data-img="${c.img}"`:''}>
    <header class="rch"><span><b>${c.t}</b><span class="rcs">${c.sub||''}</span></span><span class="rcc"></span></header>
    ${c.img?`<button type="button" class="rtc" data-cap="${c.img[0]}">${ic('camera')}<b>Chụp bằng camera</b><small>${c.hint||''}</small></button><button type="button" class="rth" aria-label="Xem to ảnh đã quét" hidden></button><button type="button" class="rtk" data-cap="${c.img[0]}" hidden>Chụp lại ảnh</button>`:''}
    <div class="rcg">${c.keys.map(rvRow).join('')}</div></section>`).join('');
  const rb=$('#rvBody');
  rb.querySelectorAll('[data-k]').forEach(i=>i.addEventListener('input',e=>{onEdit(e);if(e.target.tagName==='TEXTAREA')autoGrow(e.target);}));
  rb.querySelectorAll('textarea.ei').forEach(autoGrow);
  $('#rvDen').addEventListener('input',onRvDen);$('#rvDen').addEventListener('focus',e=>setTimeout(()=>e.target.select(),0));
  const mi=rb.querySelector('[data-k="mau"]');if(mi){mi.readOnly=true;mi.setAttribute('inputmode','none');mi.onclick=openMau;}
  rb.querySelectorAll('input.ei').forEach(i=>i.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();const all=[...rb.querySelectorAll('input.ei:not([readonly]),textarea.ei')],n=all[all.indexOf(i)+1];if(n)n.focus();else $('#rvNext').click();}}));
  paintReview();paintRvImgs();
}
let rvManual=false;   // bấm "Nhập tay": hiện ô cho cả khi chưa có ảnh
const RV_DEFAULT=['le_phi','so_ngay','tu_ngay'];   // ô có giá trị mặc định lấy từ Cài đặt
function paintReview(){
  const rb=$('#rvBody');if(!rb||!rb.firstChild)return;
  const t0=parseD(val('tu_ngay')),d=+val('so_ngay')||0;
  rb.querySelectorAll('.rv').forEach(r=>{
    const k=r.dataset.row,s=st(k),i=r.querySelector('[data-k]');
    r.classList.remove('ok','check','missing');r.classList.add(s.status);
    i.classList.remove('ok','check','missing');i.classList.add(s.status);
    if(document.activeElement!==i){const v=(k==='so_tien'||k==='le_phi')&&s.value?money(s.value):s.value;if(i.value!==v){i.value=v;if(i.tagName==='TEXTAREA')autoGrow(i);}}
    const df=RV_DEFAULT.includes(k)&&s.status==='ok'&&/^Mặc định/.test(s.note||'');
    const chip=df?'<span class="chip df">Mặc định</span>':s.value?(s.status==='ok'?'<span class="chip ok">Đã đọc</span>':s.status==='check'?`<button type="button" class="tipb" data-tip="${k}" aria-label="Cần soát: bấm xem lý do">Kiểm tra</button>`:'<span class="chip missing">Chưa đúng</span>'):(s.status==='missing'?'<span class="chip missing">Cần nhập</span>':'');
    const nt=s.note&&!df&&s.status!=='check'&&!/^Chưa có thông tin/.test(s.note)&&(s.status!=='ok'||!s.edited)?`<span class="nt">${esc(s.note)}</span>`:'';
    const h=chip+nt;const m=r.querySelector('.rvm');if(m.dataset.h!==h){m.innerHTML=h;m.dataset.h=h;}
    const hh=r.querySelector('.rvh');
    if(k==='so_tien'){const n=+s.value||0;hh.textContent=n>0?words(n):'';hh.hidden=!(n>0);}
  });
  paintRvImgs();
  const dn=$('#rvDen');if(document.activeElement!==dn){dn.value=t0&&d?fmtD(new Date(t0.getTime()+d*86400000)):'';dn.classList.remove('missing');}
  const miss=missingFields(),chk=checkFields(),mk=new Set(miss.map(f=>f.k)),ck=new Set(chk.map(f=>f.k));
  rb.querySelectorAll('.rcd').forEach(c=>{
    const keys=REVIEW_CARDS.find(x=>x.id===c.dataset.card).keys,m=keys.filter(k=>mk.has(k)).length,w=keys.filter(k=>ck.has(k)).length;
    const sm=RV_SUM[c.dataset.card];
    const fold=!!(sm&&c.dataset.img.split(',').some(k=>files[k])&&!m&&!w&&c.dataset.open!=='1'&&!c.contains(document.activeElement));
    c.classList.toggle('fold',fold);if(fold)c.querySelector('.rcs').textContent=sm();
    const o=c.querySelector('.rcc');o.className='rcc chip '+(m?'missing':w?'check':'ok');o.textContent=m?`Thiếu ${m}`:w?`Cần soát ${w}`:'Đủ';
  });
  rb.querySelectorAll('textarea.ei').forEach(t=>{if(t.offsetParent)autoGrow(t);});   // ô nhiều dòng: tính lại chiều cao khi thẻ đã hiện (lúc ẩn/thu gọn đo ra 0 nên bị cắt chữ)
  const n=$('#rvNote'),nm=f=>(RV_LBL[f.k]||f.l).replace(/\s*\(.*\)/,'');
  n.className='wnote '+(miss.length?'bad':chk.length?'warn':'ok');
  if(miss.length){n.innerHTML=`<span class="n">${miss.length}</span><span class="t"><b>Cần nhập:</b> ${esc(miss.slice(0,3).map(nm).join(', '))}${miss.length>3?'…':''}</span><span class="go">Nhập ›</span>`;n.dataset.first=miss[0].k;}else{delete n.dataset.first;n.textContent=chk.length?`${chk.length} ô máy chưa chắc, so lại với giấy tờ rồi xác nhận`:'Thông tin đã đủ, bấm xác nhận';}
}
$('#rvNote').onclick=()=>{const k=$('#rvNote').dataset.first;if(!k)return;const i=document.querySelector(`#rvBody [data-k="${k}"]`);if(i){i.scrollIntoView({block:'center',behavior:'smooth'});setTimeout(()=>i.focus({preventScroll:true}),350);}};
/* Dòng tóm tắt khi thẻ giấy tờ đã đủ và được thu gọn */
const RV_SUM={cccd:()=>[val('ho_ten'),val('cccd')].filter(Boolean).join(' · '),cavet:()=>[val('bks'),val('nhan_hieu'),val('mau')].filter(Boolean).join(' · ')};
/* Sửa "Đến ngày" thì số ngày tự khớp lại (và ngược lại: sửa số ngày/từ ngày thì đến ngày tự tính ở paintReview) */
function onRvDen(e){
  const t=e.target,x=t.value.replace(/\D/g,'').slice(0,8);
  t.value=x.length>4?`${x.slice(0,2)}/${x.slice(2,4)}/${x.slice(4)}`:x.length>2?`${x.slice(0,2)}/${x.slice(2)}`:x;
  const d1=parseD(t.value),t0=parseD(val('tu_ngay'));
  if(!d1||!t0){t.classList.toggle('missing',t.value.length===10);return;}
  const n=Math.round((d1-t0)/86400000);t.classList.toggle('missing',n<=0);
  if(n>0){state.so_ngay={value:String(n),status:'ok',note:'',edited:true};const si=document.querySelector('#rvBody [data-k=so_ngay]');if(si)si.value=n;refresh();}
}
