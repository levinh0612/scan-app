const NGUON={may_tinh:'tạo trên máy tính',dien_thoai:'tạo trên điện thoại'};   // nơi tạo hồ sơ (server tự ghi theo thiết bị gửi lên)
/* --- Danh sách hợp đồng --- */
const FILTERS=[['','Tất cả'],['dang_cam','Đang cầm'],['qua_han','Quá hạn'],['sap_han','Sắp hạn'],['da_chuoc','Đã chuộc'],['thanh_ly','Thanh lý'],['huy','Đã hủy']];
function bkLine(st){   // dòng sao lưu trong Cài đặt: bản tự lưu mỗi ngày trong máy + nút tải về
  return `<div class="bkl ok">${ic('check')}<span class="bt"><span class="bl1"><b>Lần cuối</b> ${esc(st.sao_luu||'chưa có')}</span><span class="bs">Tự lưu mỗi ngày trong máy, giữ 30 ngày. <a class="bkdl" href="/api/contracts/backup/download" download>Tải bản sao lưu về máy</a></span></span>${qh('sl')}</div>`;
}
async function hdHome(){
  hdOpen=0;hdOpenView('tabHd');
  const st=await hdStatsRefresh();
  if(!st){if(AU.authed){hdClose();toast('Không tải được dữ liệu từ máy ở tiệm.');return;}hdPin(hdHome);return;}
  const card=(f,l,v,c='')=>`<button type="button" class="${c} ${hdFilter===f?'on':''}" data-f="${f}"><small>${l}</small><b>${v}</b></button>`;
  hdPaint(`${hdSeg('hd')}<div class="hdtop"><div><h2>Hợp đồng</h2><div class="hdsub">Tra cứu, gia hạn và chuộc đồ. ${qh('quy')}</div></div><div style="display:flex;gap:8px;align-items:center">${AU.local?'<a class="btn secondary sm" href="/api/contracts/export.csv" download>Xuất Excel<span class="dl">(CSV)</span></a><button class="btn primary sm dnew" id="hdNew" type="button">+ Hồ sơ mới</button>':'<button class="btn secondary sm" id="hdLock" type="button">'+ic('lock')+' Khóa</button>'}</div></div>
  <div class="hdst">${card('dang_cam','Đang cầm',st.dang_cam+(AU.local?`<em>Vốn ${money(st.von_dang_cam)}đ</em>`:''))}${card('qua_han','Quá hạn',st.qua_han,'bad')}${card('sap_han','Sắp đến hạn',st.sap_han,'warn')}${card('da_chuoc','Đã chuộc',st.da_chuoc)}${AU.local?`<button type="button" class="vn" id="hdVon"><small>Vốn đang bỏ ra ${qh('von')}</small><b>${money(st.von_dang_cam)}</b></button>`:''}</div>
  <div class="hdbar"><input class="hdq" id="hdQ" type="search" placeholder="Tìm biển số, tên, SĐT, mã HĐ…" value="${esc(hdQ)}" autocomplete="off">${hdFltHtml()}</div>
  <div id="hdList"></div>`);
  const nw=$('#hdNew');if(nw)nw.onclick=()=>{$('#tabHome').click();if(window.homeStart)homeStart('top');};
  const lk=$('#hdLock');if(lk)lk.onclick=lockNow;
  hdFltBind();
  let t;$('#hdQ').oninput=e=>{clearTimeout(t);t=setTimeout(()=>{hdQ=e.target.value;hdList();},300);};
  hdList();
}
// Chữ hạn ngắn cho dòng danh sách: "Quá 3 ngày", "Còn 5 ngày" hoặc ngày đến hạn dd/mm
function hdHanText(c){const n=c.con_ngay;
  if(n==null)return c.den_ngay_vn||'';
  if(n<0)return 'Quá '+(-n)+' ngày';
  if(n===0)return 'Hôm nay';
  if(n<=7)return 'Còn '+n+' ngày';
  return (c.den_ngay_vn||'').slice(0,5);}
async function hdList(){
  const box=$('#hdList');if(!box)return;
  try{
    const r=await api(`/api/contracts?q=${encodeURIComponent(hdQ)}&status=${hdFilter}`);
    const row=c=>{
      const xe=[c.nhan_hieu,c.so_loai].filter(Boolean).join(' ');
      const tone=c.hien_thi==='qua_han'?'bad':c.hien_thi==='sap_han'?'warn':'';
      const q=c.status==='dang_cam'?`<button type="button" class="q1" data-q="renew">Gia hạn</button><button type="button" class="q2" data-q="chuoc">Chuộc</button><button type="button" class="q3" data-q="nhac">Nhắc</button>`:`<button type="button" class="q4" data-q="inlai">In lại</button>`;
      return `<div class="hdsw"><div class="hdact">${q}</div><button type="button" class="hdrow" data-id="${c.id}"><span class="a">${esc(c.ho_ten)||'(chưa có tên)'}</span><span class="r">${AU.local?money(c.so_tien)+'đ':''}</span><span class="b"><b class="pl">${esc(c.bks)}</b> <i>· ${esc(c.ma)}</i></span><span class="r ht ${tone}">${c.status==='dang_cam'?esc(hdHanText(c)):bdg(c)}</span>
        <span class="tb m">${esc(c.ma)}</span><span class="tb k"><b>${esc(c.ho_ten)||'(chưa có tên)'}</b><small>${esc(c.sdt||'')}</small></span><span class="tb x"><b>${esc(xe)||'—'}</b><small>${esc(c.bks)}</small></span><span class="tb h ${tone}">${esc(c.den_ngay_vn)}</span><span class="tb t">${AU.local?money(c.so_tien)+'đ':''}</span><span class="tb s">${bdg(c)}</span></button></div>`;};
    box.innerHTML=r.items.length?`<div class="hdth"><span>Mã</span><span>Khách</span><span>Xe</span><span>Đến hạn</span><span>Số tiền</span><span>Trạng thái</span></div>`+r.items.map(row).join('')+`<p class="hdev">Hiển thị ${r.items.length} trên ${r.total} hợp đồng${r.total>r.items.length?' — gõ tìm để thu hẹp':''}.</p>`:`<div class="empty"><div>${ic('inbox')}</div><b>${hdQ||hdFilter?'Không có hợp đồng nào khớp':'Chưa có hợp đồng nào'}</b><span>${hdQ||hdFilter?'Thử bỏ bộ lọc hoặc gõ từ khóa khác.':'Hợp đồng sẽ xuất hiện ở đây sau khi in phiếu.'}</span></div>`;
    box.querySelectorAll('.hdrow').forEach(b=>b.onclick=()=>hdShow(+b.dataset.id));
    hdSwipeBind(box);
  }catch(e){if(e.status===401){hdPin(hdHome);return;}box.innerHTML='<div class="empty"><div>'+ic('warn')+'</div><b>Không tải được danh sách</b><span>Kiểm tra máy ở tiệm còn mở và kết nối mạng.</span></div>';}
}

