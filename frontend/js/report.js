/* --- Báo cáo (chỉ máy tính ở tiệm) --- */
let rpP='thang';
function rpRange(p){
  const n=new Date(),y=n.getFullYear(),m=n.getMonth();
  if(p==='thang')return [iso(new Date(y,m,1)),iso(new Date(y,m+1,0))];
  if(p==='truoc')return [iso(new Date(y,m-1,1)),iso(new Date(y,m,0))];
  if(p==='quy')return [iso(new Date(y,m-2,1)),iso(new Date(y,m+1,0))];
  if(p==='nam')return [iso(new Date(y,0,1)),iso(new Date(y,11,31))];
  return null;
}
async function hdReport(frm,to){
  hdOpenView('tabRp');
  await authInit();if(!AU.local){hdClose();toast('Báo cáo chỉ xem được trên máy tính ở tiệm.');return;}
  if(!frm){const r=rpRange(rpP);if(r)[frm,to]=r;}
  let r;try{r=await api(`/api/contracts/report?frm=${frm||''}&to=${to||''}`);}catch(e){hdPaint('<div class="empty"><div>'+ic('warn')+'</div><b>Không tải được báo cáo</b></div>');return;}
  const P=[['thang','Tháng này'],['truoc','Tháng trước'],['quy','3 tháng'],['nam','Năm nay'],['tuy','Tùy chọn']];
  const kp=(l,v,k,c='')=>`<div class="kpi ${c}"><small>${l} ${qh(k)}</small><b>${v}</b></div>`;
  const row=(l,v,k,c='')=>`<div class="kv"><span>${l}${k?' '+qh(k):''}</span><b class="${c}">${v}</b></div>`;
  const sg=n=>(n>0?'+':n<0?'−':'')+money(Math.abs(n))+' đ';
  const mx=Math.max(1,...r.chuoi.map(x=>Math.abs(x.loi_nhuan)));
  hdPaint(`${hdSeg('rp')}<div class="hdtop"><h2>Báo cáo ${qh('quy')}</h2><a class="btn secondary sm" href="/api/contracts/export.csv" download>Xuất Excel</a></div>
  <div class="fchips">${P.map(p=>`<button type="button" class="${rpP===p[0]?'on':''}" data-p="${p[0]}">${p[1]}</button>`).join('')}</div>
  ${rpP==='tuy'?`<div class="fgrid" style="margin:8px 0"><label class="fl">Từ ngày<input type="date" id="rF" value="${esc(r.tu)}"></label><label class="fl">Đến ngày<input type="date" id="rT" value="${esc(r.den)}"></label></div><button class="btn primary sm" id="rGo" type="button">Xem</button>`:''}
  <p class="hdnote">Kỳ báo cáo: <b>${esc(r.tu.split('-').reverse().join('/'))}</b> → <b>${esc(r.den.split('-').reverse().join('/'))}</b></p>
  <div class="kpis">${kp('Vốn đang bỏ ra',money(r.von_dang_cam)+' đ','von')}${kp('Doanh thu',money(r.doanh_thu)+' đ','dt')}${kp('Lợi nhuận',sg(r.loi_nhuan),'ln',r.loi_nhuan<0?'neg':'pos')}${kp('Tỷ suất',r.ty_suat+'%','ts')}</div>
  <p class="hdnote">Đang cầm: <b>${r.so_dang_cam}</b> hợp đồng.</p>
  <div class="rpg"><div class="grp rpdt"><h4>Doanh thu trong kỳ ${qh('dt')}</h4>${row('Lệ phí lúc cầm',money(r.le_phi_tao)+' đ')}${row('Phí gia hạn',money(r.le_phi_gia_han)+' đ')}${row(`Lệ phí khi chuộc (${r.so_chuoc} HĐ)`,money(r.le_phi_chuoc)+' đ')}${row('Cộng doanh thu',money(r.doanh_thu)+' đ')}</div>
  <div class="rpr"><div class="grp"><h4>Thanh lý ${qh('tl')}</h4>${row(`Lãi/lỗ thanh lý (${r.so_thanh_ly} HĐ)`,sg(r.lai_lo_thanh_ly),'',r.lai_lo_thanh_ly<0?'neg':'pos')}${r.thanh_ly_chua_gia?row('Chưa nhập giá bán (chưa tính)',r.thanh_ly_chua_gia+' HĐ'):''}</div>
  <div class="grp"><h4>Dòng vốn (không phải doanh thu)</h4>${row('Cho cầm mới',money(r.cho_cam_moi)+' đ')}${row('Thu hồi gốc từ chuộc',(r.thu_hoi_goc>0?'+':'')+money(r.thu_hoi_goc)+' đ','thu_hoi')}</div>
  </div>
  <div class="grp"><h4>Lợi nhuận 6 tháng gần nhất</h4>${r.chuoi.some(x=>x.loi_nhuan)?'':'<p class="hdnote">Chưa có lợi nhuận trong 6 tháng này.</p>'}<div class="chart">${r.chuoi.map(x=>`<div class="bar"><div class="bv ${x.loi_nhuan<0?'neg':''}" style="height:${Math.max(4,Math.round(Math.abs(x.loi_nhuan)/mx*100))}px" title="${sg(x.loi_nhuan)}"></div><small>${esc(x.thang)}</small><small class="bn">${sg(x.loi_nhuan)}</small></div>`).join('')}</div></div></div>`);
  document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{rpP=b.dataset.p;hdReport();});
  const go=$('#rGo');if(go)go.onclick=()=>hdReport($('#rF').value,$('#rT').value);
}

