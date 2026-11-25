/* --- Ảnh đã quét (cần PIN nên tải bằng fetch có header) --- */
const KIND_LBL={cccd:'CCCD mặt sau',cavet:'Cà vẹt'};
async function imgURL(id,kind){
  const r=await fetch(`/api/contracts/${id}/anh/${kind}`,{headers:AU.tok?{'X-Session':AU.tok}:{}});
  if(!r.ok)throw new Error(r.status);return URL.createObjectURL(await r.blob());
}
async function loadThumbs(id,kinds,root='#hdDlg'){
  for(const k of kinds){
    const el=document.querySelector(`${root} [data-img="${k}"]`);if(!el)continue;
    try{const u=await imgURL(id,k);el.style.backgroundImage=`url(${u})`;el.dataset.u=u;el.classList.add('has');}catch(e){el.textContent='Không tải được ảnh';}
  }
}
function viewImages(c,kinds){
  if(!kinds.length)return toast('Hợp đồng này chưa có ảnh đã quét.');
  sheet(shHead('Ảnh đã quét · '+esc(c.ma),'anh')+`<div class="imgs">${kinds.map(k=>`<figure><div class="big" data-img="${k}">Đang tải…</div><figcaption>${KIND_LBL[k]}</figcaption></figure>`).join('')}</div>`,shBind);
  loadThumbs(c.id,kinds,'#sheet');
  $('#sheet').querySelectorAll('.imgs .big').forEach(b=>b.addEventListener('click',()=>{if(b.dataset.u)zoomImage(b.dataset.u,KIND_LBL[b.dataset.img]);}));
}
/* Phóng to ảnh toàn màn hình: chạm ảnh để phóng/thu, kéo để xem các góc, X hoặc Esc để đóng */
function zoomImage(u,label){
  let z=$('#imgZoom');if(z)z.remove();
  z=document.createElement('div');z.id='imgZoom';z.setAttribute('role','dialog');z.setAttribute('aria-label',label||'Ảnh');
  z.innerHTML=`<div class="izs"><img alt="${esc(label||'')}" src="${u}"></div><button type="button" class="izx" aria-label="Đóng">${ic('x')}</button><div class="izh">Chạm ảnh để phóng to / thu nhỏ</div>`;
  document.body.appendChild(z);
  const s=z.querySelector('.izs'),im=z.querySelector('img');
  const close=()=>{z.remove();document.removeEventListener('keydown',esc_);};
  const esc_=e=>{if(e.key==='Escape')close();};document.addEventListener('keydown',esc_);
  z.querySelector('.izx').onclick=close;
  let moved=false,sx=0,sy=0;
  s.addEventListener('pointerdown',e=>{moved=false;sx=e.clientX;sy=e.clientY;});
  s.addEventListener('pointermove',e=>{if(Math.abs(e.clientX-sx)+Math.abs(e.clientY-sy)>6)moved=true;});
  s.addEventListener('click',e=>{if(moved)return;
    if(e.target===s&&!z.classList.contains('zoomed')){close();return;}
    const on=z.classList.toggle('zoomed');
    if(on){requestAnimationFrame(()=>{s.scrollLeft=(s.scrollWidth-s.clientWidth)/2;s.scrollTop=(s.scrollHeight-s.clientHeight)/2;});}
  });
}

/* --- Chi tiết hợp đồng --- */

