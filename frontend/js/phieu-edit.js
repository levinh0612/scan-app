/* ================= Phiếu: bấm vào ô để sửa ================= */
const LBL=Object.fromEntries(FIELDS.filter(f=>f.k).map(f=>[f.k,f.l]));
const NOTE_KEYS=['ho_ten','dia_chi','cccd','sdt','ngay_cap','nhan_hieu','so_loai','mau','bks','so_khung','so_may','so_tien','tu_ngay'];
const st=k=>state[k]||(state[k]={value:'',...validate(k,'')});
function inp(k,o={}){const s=st(k);
  return `<input class="ei ${s.status} ${o.cls||''}" data-k="${k}" value="${esc((k==='so_tien'||k==='le_phi')&&s.value?money(s.value):s.value)}" inputmode="${o.mode||'text'}" enterkeyhint="next" autocomplete="off" autocapitalize="off" ${o.max?`maxlength="${o.max}"`:''} ${o.ph?`placeholder="${o.ph}"`:''} aria-label="${esc(LBL[k]||k)}">`;}
function txa(k){const s=st(k);return `<textarea rows="1" class="ei ${s.status}" data-k="${k}" autocomplete="off" autocapitalize="off" aria-label="${esc(LBL[k]||k)}">${esc(s.value)}</textarea>`;}
function autoGrow(t){t.style.height='auto';t.style.height=t.scrollHeight+'px';}
function dateIn(k){const s=st(k),p=(s.value||'').split('/');
  const one=(i,cls,max,ph)=>`<input class="ei ${s.status} ${cls}" data-dk="${k}" data-p="${i}" value="${esc(p[i]||'')}" inputmode="numeric" maxlength="${max}" placeholder="${ph}" autocomplete="off" aria-label="${esc(LBL[k])} — ${['ngày','tháng','năm'][i]}">`;
  return `${one(0,'d2',2,'ng')}<label>tháng</label>${one(1,'d2',2,'th')}<label>năm</label>${one(2,'d4',4,'năm')}`;}
const note=k=>`<div class="pshot" id="c-${k}" hidden><span>Trên giấy tờ</span><img alt="Chữ trên giấy tờ"></div><div class="pnote" id="n-${k}"></div>`;
function renderPhieu(){
  const [dd,mm,yy]=today().split('/');
  $('#phieu').innerHTML=`<h3 class="pt">HỢP ĐỒNG CẦM ĐỒ</h3><div class="psub">( Kiêm Phiếu Chi Tiền )</div>
  <div class="pr"><label>Họ và tên ông ( bà ):</label>${inp('ho_ten')}<i>Đại diện cầm đồ</i></div>${note('ho_ten')}
  <div class="pr"><label>Địa chỉ:</label>${txa('dia_chi')}</div>${note('dia_chi')}
  <div class="pr"><label>Cmt số ( hoặc giấy tờ tùy thân khác ):</label>${inp('cccd',{mode:'numeric',max:12})}</div>${note('cccd')}
  <div class="pr"><label>Cấp ngày</label>${dateIn('ngay_cap')}</div>${note('ngay_cap')}
  <div class="pr"><label>Điện thoại:</label>${inp('sdt',{mode:'tel'})}</div>${note('sdt')}
  <div class="pr"><label>Tôi xin thỏa thuận tự nguyện đặt đồ vật, tài sản kê sau đây:</label></div>
  <div class="pr"><label>Nhãn hiệu - loại:</label><span class="pair">${inp('nhan_hieu',{ph:'hãng'})}<i>-</i>${inp('so_loai',{ph:'loại'})}</span></div>${note('nhan_hieu')}
  <div class="pr"><label>Màu sơn:</label>${inp('mau')}</div>${note('mau')}
  <div class="pr"><label>Biển số:</label>${inp('bks')}</div>${note('bks')}
  <div class="pr"><label>Số khung:</label>${inp('so_khung')}</div>${note('so_khung')}
  <div class="pr"><label>Số máy:</label>${inp('so_may')}</div>${note('so_may')}
  <div class="pr"><label>Lệ phí thỏa thuận:</label>${inp('le_phi',{mode:'numeric'})}<label id="a-fmt2">đồng</label></div>
  <div class="pr"><label>Tôi đã nhận đủ số tiền mà cửa hàng đã giao</label></div>
  <div class="pr"><label>Số tiền viết bằng chữ:</label><span class="auto" id="a-words"></span></div>
  <div class="pr"><label>Số tiền viết bằng số:</label>${inp('so_tien',{mode:'numeric'})}<label id="a-fmt">đồng</label></div>${note('so_tien')}
  <div class="pr"><label>- Từ ngày</label>${dateIn('tu_ngay')}</div>${note('tu_ngay')}
  <div class="pr"><label>- Đến ngày</label><input class="ei" id="a-den" inputmode="numeric" maxlength="10" placeholder="ngày/tháng/năm" autocomplete="off" aria-label="Đến ngày"><label>(cầm</label>${inp('so_ngay',{mode:'numeric',cls:'short'})}<label>ngày)</label></div>
  <div class="legal2">Hiệu cầm đồ được quyền quản lý, điều động khi cần thiết, khi hết hạn mà không có tiền chuộc lại, tôi đồng ý bán đồ vật cầm, ngang bằng tôi đã nhận của cửa hàng.
    <div class="it">- Cửa hàng có quyền bán ( thu vốn )</div><div class="it">- Lời thì cửa hàng được hưởng.</div><div class="it">- Lỗ thì cửa hàng phải chịu.</div>
    Tôi không hề thắc mắc, khiếu kiện, nhờ cậy ai.<br>Số tài sản tôi mang cầm chính là tài sản của tôi. Quyền định đoạt cao nhất là tôi, số tài sản này không tranh chấp hoặc cầm cố bất kỳ cá nhân , tổ chức hoặc ngân hàng tín dụng nào.<br>Nếu có điều gì man trá, sai trái tôi xin chịu trách nhiệm trước Pháp luật Nhà nước.</div>
  <div class="pr end"><label>Ngày ${dd} tháng ${mm} năm ${yy}</label></div>
  <div class="sign2"><div>Phụ trách cửa hàng</div><div>Người nhận tiền<small>( Ký, ghi rõ họ tên )</small></div></div>`;
  const ph=$('#phieu');
  ph.querySelectorAll('[data-k]').forEach(i=>i.addEventListener('input',onEdit));
  const mi=ph.querySelector('[data-k="mau"]');if(mi){mi.readOnly=true;mi.setAttribute('inputmode','none');mi.placeholder='Bấm để chọn màu';mi.onclick=openMau;}
  ph.querySelectorAll('[data-dk]').forEach(i=>i.addEventListener('input',onDate));
  const dn=$('#a-den');if(dn){dn.addEventListener('input',onDen);dn.addEventListener('blur',updateAuto);}
  ph.querySelectorAll('textarea.ei').forEach(t=>{autoGrow(t);t.addEventListener('input',()=>{autoGrow(t);fitPhieu();});});
  updateAuto();refresh();
}
function onEdit(e){
  const k=e.target.dataset.k;let v=e.target.value;
  if(k==='sdt'){v=v.replace(/\D/g,'').slice(0,11);e.target.value=v;}
  if(k==='ngay_cap'||k==='tu_ngay'){const d=v.replace(/\D/g,'').slice(0,8);v=d.length>4?`${d.slice(0,2)}/${d.slice(2,4)}/${d.slice(4)}`:d.length>2?`${d.slice(0,2)}/${d.slice(2)}`:d;e.target.value=v;}
  if(['cccd','so_tien','le_phi','so_ngay'].includes(k)){v=v.replace(/\D/g,'');e.target.value=(k==='so_tien'||k==='le_phi')&&v?money(v):v;}
  state[k]={value:v,...validate(k,v),edited:true};updateAuto();refresh();
  if(DUP_KEYS.includes(k)||k==='ho_ten')dupCheck();
}
function onDate(e){
  const t=e.target,k=t.dataset.dk,i=+t.dataset.p,ph=$('#phieu');t.value=t.value.replace(/\D/g,'');
  if(t.value.length===t.maxLength&&i<2)ph.querySelector(`[data-dk="${k}"][data-p="${i+1}"]`).focus();
  const parts=[0,1,2].map(j=>ph.querySelector(`[data-dk="${k}"][data-p="${j}"]`).value.trim());
  const v=parts.every(x=>!x)?'':parts.map((x,j)=>j<2?x.padStart(2,'0'):x).join('/');
  state[k]={value:v,...validate(k,v),edited:true};updateAuto();refresh();
}
function onDen(e){
  const t=e.target;let v=t.value.replace(/[^\d]/g,'').slice(0,8);
  t.value=v.length>4?v.slice(0,2)+'/'+v.slice(2,4)+'/'+v.slice(4):v.length>2?v.slice(0,2)+'/'+v.slice(2):v;
  const d1=parseD(t.value),t0=parseD(val('tu_ngay'));
  if(d1&&t0){const n=Math.round((d1-t0)/86400000);
    if(n>0){state.so_ngay={value:String(n),status:'ok',note:'',edited:true};const si=document.querySelector('[data-k=so_ngay]');if(si)si.value=n;t.classList.remove('missing');}
    else{t.classList.add('missing');}}
  refresh();
}
function updateAuto(){
  const n=+val('so_tien')||0;$('#a-words').textContent=n>0?words(n):'';
  $('#a-fmt').textContent='đồng';
  const lp=+val('le_phi')||0;$('#a-fmt2').textContent='đồng';
  const d=+val('so_ngay')||0,t0=parseD(val('tu_ngay'));
  const den=$('#a-den');if(den&&document.activeElement!==den)den.value=t0&&d?fmtD(new Date(t0.getTime()+d*86400000)):'';
}
function paintSw(){const w=mauList();document.querySelectorAll('#sw button').forEach(b=>b.classList.toggle('on',w.includes(b.dataset.c)));
  const x=$('#swx');if(!x)return;const cat=MAU_CHIPS.map(c=>c[0]);
  x.innerHTML=w.filter(c=>!cat.includes(c)).map(c=>`<button type="button" class="on" data-x="${esc(c)}">${esc(c)} ${ic('x')}</button>`).join('');   // màu ngoài danh sách: bấm để bỏ
  x.querySelectorAll('button').forEach(b=>b.onclick=()=>{setMau(mauList().filter(y=>y!==b.dataset.x));paintSw();});}
const crops={};   // ảnh cắt quanh chữ trên giấy tờ (từ máy chủ) để đối chiếu; không lưu vào phiếu
function paintStatus(){paintSw();
  document.querySelectorAll('#phieu .pshot').forEach(b=>{const c=crops[b.id.slice(2)],im=b.querySelector('img');if(c){if(im.src!==c){im.onload=()=>im.classList.toggle('tall',im.naturalHeight/im.naturalWidth>.09);im.src=c;}b.hidden=false;}else b.hidden=true;});
  document.querySelectorAll('#phieu [data-k],#phieu [data-dk]').forEach(i=>{const s=st(i.dataset.k||i.dataset.dk);i.classList.remove('ok','check','missing');i.classList.add(s.status);});
  NOTE_KEYS.forEach(k=>{const el=$('#n-'+k);if(!el)return;const s=st(k);
    el.innerHTML=s.value&&s.note&&s.status!=='ok'?(s.status==='check'?ic('warn')+' ':'')+esc(s.note):'';});
}

