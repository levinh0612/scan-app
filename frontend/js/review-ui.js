/* ================= Bước 2 · ảnh đã quét nằm trong từng thẻ + xem ảnh to ================= */
const _blobUrl=new WeakMap();
const blobUrl=f=>{if(!_blobUrl.has(f))_blobUrl.set(f,URL.createObjectURL(f));return _blobUrl.get(f);};

/* Mỗi thẻ giấy tờ: chưa có ảnh → ô chụp + ẩn các ô nhập; có ảnh → ảnh nhỏ + các ô đọc được; thẻ Khoản cầm hiện khi đã có ô nào đó */
function paintRvImgs(){
  const cards=[...document.querySelectorAll('#rvBody .rcd')];
  const show=c=>{const d=c.dataset.img,ks=REVIEW_CARDS.find(x=>x.id===c.dataset.card).keys;return rvManual||(d?d.split(',').some(k=>files[k]):false)||ks.some(k=>k!=='den'&&val(k)&&!RV_DEFAULT.includes(k));};
  cards.forEach(c=>{
    if(!c.dataset.img)return;
    const k=c.dataset.img.split(',').find(x=>files[x]),t=c.querySelector('.rth');
    t.hidden=c.querySelector('.rtk').hidden=!k;c.querySelector('.rtc').hidden=!!k;t.dataset.img=k||'';
    t.style.backgroundImage=k?`url(${blobUrl(files[k])})`:'';
    if(!c.classList.contains('fold'))c.querySelector('.rcs').textContent=k?'Đối chiếu ảnh với các ô bên dưới':'Chụp bằng camera, app tự điền các ô';
    c.classList.toggle('rnone',!show(c));
  });
  const cam=document.querySelector('#rvBody .rcd[data-card=cam]');
  if(cam)cam.classList.toggle('rnone',!cards.some(c=>c!==cam&&!c.classList.contains('rnone')));
  $('#rvBody').classList.toggle('both',!!(files.cccd_back&&files.cavet));   // đã có đủ 2 giấy tờ: đưa "Cần nhập thêm" lên đầu
  const any=cards.some(c=>!c.classList.contains('rnone')&&c.dataset.card!=='cam');
  $('#rvNext').disabled=!any||document.body.classList.contains('scanning');
  $('#btnSkip').hidden=any;$('#w2 .wbar').classList.toggle('idle',!any);   // chưa có gì để xác nhận thì ẩn thanh dưới, khỏi che ô chụp
}
/* Chụp ảnh cho thẻ: camera trực tiếp, không có thì hộp chọn ảnh của hệ điều hành */
function pickPhoto(k){
  if(camOK())return openCam(k);
  const i=document.createElement('input');i.type='file';i.accept='image/*';i.capture='environment';
  i.onchange=()=>{if(i.files[0])setFile(k,i.files[0]);};i.click();
}
$('#rvBody').addEventListener('click',e=>{
  const h=e.target.closest('.rcd.fold .rch,.rcd[data-open="1"] .rch');if(h){const c=h.parentNode;c.dataset.open=c.classList.contains('fold')?'1':'';paintReview();return;}
  const c=e.target.closest('[data-cap]');if(c)return pickPhoto(c.dataset.cap);
  const b=e.target.closest('.rth');if(b&&files[b.dataset.img])openLightbox(blobUrl(files[b.dataset.img]));
});

function openLightbox(url){
  const lb=document.createElement('div');lb.className='lightbox';lb.setAttribute('role','dialog');lb.setAttribute('aria-label','Ảnh đã quét');
  lb.innerHTML=`<img alt="Ảnh đã quét phóng to" src="${url}"><button type="button" aria-label="Đóng">${ic('x')}</button>`;
  const close=()=>{lb.remove();removeEventListener('keydown',esc_);};
  const esc_=e=>{if(e.key==='Escape')close();};
  lb.addEventListener('click',close);addEventListener('keydown',esc_);document.body.appendChild(lb);
}

/* Bước In phiếu: Tờ 1 CCCD, Tờ 2 cà vẹt chỉ để đối chiếu (lệnh in chỉ gửi chữ điền vào giấy mẫu); Tờ 3 là phiếu bên dưới */
const SHEETS=[{t:'Tờ 1 · CCCD',img:'cccd_back',rows:['ho_ten','cccd','ngay_cap','dia_chi']},{t:'Tờ 2 · Cà vẹt xe',img:'cavet',rows:['bks','nhan_hieu','so_loai','mau','so_may','so_khung']}];
function paintSheets(){
  const el=$('#w3sheets');if(!el||document.body.dataset.w!=='3')return;
  el.innerHTML=SHEETS.map(c=>`<section class="shc"><header><b>${c.t}</b><span>Để đối chiếu, không in</span></header><div class="shb">${files[c.img]?`<img src="${blobUrl(files[c.img])}" alt="">`:''}<dl>${c.rows.map(k=>`<div><dt>${esc(RV_LBL[k]||k)}</dt><dd>${esc(val(k))||'—'}</dd></div>`).join('')}</dl></div></section>`).join('');
}

/* Dấu "!" ở ô cần soát: bấm hiện khung giải thích + nút "Xác nhận đã đúng" */
function closeTip(){const t=$('#rvTip');if(t)t.remove();}
document.addEventListener('click',e=>{
  const b=e.target.closest('.tipb'),inTip=e.target.closest('#rvTip');
  if(inTip){const ok=e.target.closest('[data-tipok]');if(ok){const k=ok.dataset.tipok;state[k]={...st(k),status:'ok',note:'',edited:true};closeTip();refresh();}return;}
  const had=$('#rvTip'),same=had&&b&&had.dataset.k===b.dataset.tip;closeTip();
  if(!b||same)return;
  const k=b.dataset.tip,s=st(k),t=document.createElement('div');
  t.id='rvTip';t.dataset.k=k;t.setAttribute('role','dialog');
  t.innerHTML=`<b>${esc(LBL[k]||'Cần soát')}</b><p>${esc(s.note||'Máy đọc chưa chắc chắn, hãy so với giấy tờ.')}</p><button type="button" class="btn primary sm" data-tipok="${k}">Xác nhận đã đúng</button>`;
  document.body.appendChild(t);
  const r=b.getBoundingClientRect(),W=document.documentElement.clientWidth,w=Math.min(300,W-24);
  t.style.width=w+'px';t.style.left=Math.max(12,Math.min(r.right-w,W-w-12))+'px';
  const h=t.offsetHeight,below=r.bottom+8+h<innerHeight;
  t.style.top=(below?r.bottom+8:Math.max(8,r.top-8-h))+'px';
  t.style.setProperty('--ax',(r.left+r.width/2-parseFloat(t.style.left))+'px');t.classList.toggle('up',!below);
});
addEventListener('scroll',closeTip,true);addEventListener('resize',closeTip);
