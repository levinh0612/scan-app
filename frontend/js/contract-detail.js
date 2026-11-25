const EV={tao:'Lập hợp đồng',gia_han:'Gia hạn',chuoc:'Chuộc đồ',thanh_ly:'Thanh lý',mo_lai:'Mở lại',sua:'Sửa thông tin',huy:'Hủy hợp đồng'};
function dlgX(){const d=$('#hdDlg');if(d)d.hidden=true;}
function dlgPaint(h){
  let d=$('#hdDlg');
  if(!d){d=document.createElement('div');d.id='hdDlg';d.className='ddlg';d.setAttribute('role','dialog');d.setAttribute('aria-modal','true');document.body.appendChild(d);
    d.addEventListener('mousedown',e=>{if(e.target===d)dlgX();});}
  d.innerHTML=`<div class="dcard">${h}</div>`;d.hidden=false;
  d.querySelectorAll('[data-x]').forEach(b=>b.onclick=dlgX);
  const mb=$('#dMore'),mn=$('#dMenu');
  mb.onclick=e=>{e.stopPropagation();mn.hidden=!mn.hidden;d.firstChild.classList.toggle('mo',!mn.hidden);mb.setAttribute('aria-expanded',String(!mn.hidden));};
  d.onclick=e=>{if(!mn.hidden&&!e.target.closest('#dMenu .qh')){mn.hidden=true;d.firstChild.classList.remove('mo');}};   // chạm ngoài hoặc chọn mục thì đóng menu
}
async function hdShow(id){
  hdOpen=id;hdQuiet=false;
  let d;
  try{d=await api('/api/contracts/'+id);}
  catch(e){if(e.status===401){hdPin(()=>hdShow(id));return;}toast('Không mở được hợp đồng.');return;}
  const c=d.contract,act=c.status==='dang_cam',kinds=d.anh||[];
  const lan=d.events.filter(e=>e.type==='gia_han').length;
  const due=c.status==='dang_cam'&&c.con_ngay!=null?(c.con_ngay<0?`Quá hạn ${-c.con_ngay} ngày (hạn ${esc(c.den_ngay_vn)})`:c.con_ngay===0?`Đến hạn hôm nay (${esc(c.den_ngay_vn)})`:`Đến hạn ${esc(c.den_ngay_vn)} · còn ${c.con_ngay} ngày`):`Hạn ${esc(c.den_ngay_vn)}`;
  const kv=(a,b)=>`<div class="kv"><span>${a}</span><b${b?'':' class="nil"'}>${b?(a==='Địa chỉ'?addrH(b):esc(b)):'—'}</b></div>`;   // luôn hiện đủ dòng, thiếu thì ghi —
  const loc=AU.local&&c.status!=='huy';
  const grp=(t,items)=>items.length?`<div class="mg"><small>${t}</small>${items.join('')}</div>`:'';
  const it=(a,l,x='',cls='')=>`<div class="mi ${cls}"><button data-a="${a}" type="button">${l}</button>${x}</div>`;
  const tools=grp('Chốt hợp đồng',act?[it('tl','Thanh lý')]:loc?[it('molai','Mở lại hợp đồng')]:[])
    +grp('Liên hệ & giấy tờ',[...(act?[it('nhac','Nhắn nhắc hạn')]:[]),it('inlai','In lại giấy tờ')])
    +grp('Chỉnh sửa',[...(loc?[it('sua','Sửa thông tin',qh('sua'))]:[]),it('note',c.note?'Sửa ghi chú':'Thêm ghi chú')])
    +grp('Khác',[...(loc&&act?[it('huy','Hủy hợp đồng nhập nhầm','','d')]:[]),...(AU.local?[it('xoa','Xóa hẳn hồ sơ (để thử nghiệm)','','d')]:[])]);
  dlgPaint(`<div class="ddh"><div class="dtop"><b>Chi tiết hợp đồng</b><span class="dbtns"><button type="button" class="shx" id="dMore" aria-label="Thêm thao tác" aria-expanded="false">${ic('dots')}</button><button type="button" class="shx" data-x aria-label="Đóng">${ic('x')}</button></span><div class="dmenu" id="dMenu" hidden>${tools}</div></div></div>
  <div class="dbody"><div class="dh"><div class="dma">${esc(c.ma)}${act?'':' '+bdg(c)}</div><h2>${AU.local?money(c.so_tien)+' đ':esc(c.bks||c.ho_ten||c.ma)}</h2><div class="dd"><span>${due}</span>${act?qh('gh'):''}</div><div class="dsrc">${esc(NGUON[c.nguon]||'')}</div></div>
  <div class="grp"><h4>Khách hàng</h4>${kv('Họ tên',c.ho_ten)}${kv('SĐT',c.sdt)}${kv('CCCD',c.cccd)}${kv('Ngày cấp',c.ngay_cap)}${kv('Địa chỉ',c.dia_chi)}</div>
  <div class="grp"><h4>Xe</h4>${kv('Biển số',c.bks)}${kv('Loại xe',[c.nhan_hieu,c.so_loai].filter(Boolean).join(' '))}${kv('Màu sơn',c.mau)}${kv('Số khung',c.so_khung)}${kv('Số máy',c.so_may)}</div>
  <div class="grp"><h4>Khoản cầm</h4>${kv('Số tiền (gốc)',money(c.so_tien)+' đ')}${kv('Lệ phí thỏa thuận',money(c.le_phi)+' đ')}<div class="kv kr"><span>Thời hạn</span><b><em>${esc(c.tu_ngay_vn)}<i>→</i>${esc(c.den_ngay_vn)}</em><small>${c.so_ngay} ngày</small></b></div>${kv('Đã gia hạn',lan+' lần')}${c.closed_at?kv(c.status==='huy'?'Hủy lúc':'Đóng lúc',c.closed_at.slice(0,16).replace('T',' ')+(c.closed_amount?' · '+money(c.closed_amount)+' đ':'')):''}</div>
  ${c.note?`<div class="grp"><h4>Ghi chú</h4><p class="nt">${esc(c.note)}</p></div>`:''}
  ${kinds.length?`<div class="grp"><h4>Ảnh đã quét</h4><div class="thumbs">${kinds.map(k=>`<button type="button" data-a="anh"><div class="th" data-img="${k}">…</div><small>${KIND_LBL[k]}</small></button>`).join('')}</div></div>`:''}
  <div class="grp"><h4>Lịch sử</h4>${d.events.map(e=>`<div class="ev"><b>${EV[e.type]||e.type}</b><span>${esc(e.at_vn)}${e.days?` · +${e.days} ngày`:''}${e.amount?` · ${money(e.amount)}đ`:''}${e.den_ngay_vn?` · hạn mới ${esc(e.den_ngay_vn)}`:''}${e.note?` · ${esc(e.note)}`:''}</span></div>`).join('')}</div></div>
  <div class="dfoot">${act?'<button type="button" class="btn primary" data-a="renew">Gia hạn</button><button type="button" class="btn secondary" data-a="chuoc">Chuộc đồ</button>':'<button type="button" class="btn secondary" data-x>Đóng</button>'}</div>`);
  loadThumbs(id,kinds);
  const A={
    renew:()=>fRenew(c),chuoc:()=>fChuoc(c),tl:()=>fThanhLy(c),nhac:()=>fNhac(c),inlai:()=>fInLai(c,d.events),
    anh:()=>viewImages(c,kinds),note:()=>fNote(c),sua:()=>fSua(c),huy:()=>fHuy(c),xoa:()=>fXoa(c),molai:()=>fMoLai(c),
  };
  document.querySelectorAll('#hdDlg [data-a]').forEach(b=>b.onclick=()=>A[b.dataset.a]());
}
async function act(id,a,body,okMsg){
  try{await api(`/api/contracts/${id}/${a}`,{method:'POST',body:JSON.stringify(body)});sheetX();toast(okMsg);hdStatsRefresh();if($('#hdList'))hdList();const q=hdQuiet;hdQuiet=false;if(!q)hdShow(id);dupCheck(true);return true;}
  catch(e){if(e.status===401){sheetX();hdPin(()=>hdShow(id));return false;}const m=$('#shErr');if(m){m.textContent=errMsg(e);m.hidden=false;}else toast(errMsg(e));return false;}
}
const shErr='<div class="sherr" id="shErr" hidden role="alert"></div>';
const parseISO=s=>{const [y,m,d]=String(s).split('-').map(Number);return new Date(y,m-1,d);};

