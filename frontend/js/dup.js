/* ================= Hợp đồng đã lưu: cảnh báo trùng + tra cứu/gia hạn/chuộc ================= */

const phone84=p=>{p=String(p||'').replace(/\D/g,'');return p.startsWith('0')?'84'+p.slice(1):p;};
function remindText(c){
  const when=c.con_ngay==null?'':c.con_ngay<0?`đã QUÁ HẠN ${-c.con_ngay} ngày (hạn ${c.den_ngay_vn})`:c.con_ngay===0?`đến hạn HÔM NAY (${c.den_ngay_vn})`:`sẽ đến hạn ngày ${c.den_ngay_vn} (còn ${c.con_ngay} ngày)`;
  return `Chào ${c.ho_ten}, hợp đồng cầm ${[c.nhan_hieu,c.so_loai].filter(Boolean).join(' ')} biển số ${c.bks} (số tiền ${money(c.so_tien)}đ) ${when}. Anh/chị vui lòng liên hệ tiệm để gia hạn hoặc chuộc đồ. Xin cảm ơn.`;
}
function printReceipt(c,e){
  const body={c:{ma:c.ma,ho_ten:c.ho_ten,cccd:c.cccd,sdt:c.sdt,nhan_hieu:c.nhan_hieu,so_loai:c.so_loai,mau:c.mau,bks:c.bks,so_khung:c.so_khung,so_may:c.so_may,so_tien:c.so_tien},
    e:{type:e.type,at_vn:e.at_vn,days:e.days,amount:e.amount,den_ngay_vn:e.den_ngay_vn,note:e.note}};
  const T={gia_han:'Biên nhận gia hạn',chuoc:'Biên nhận chuộc đồ',thanh_ly:'Biên bản thanh lý'}[e.type]||'Biên nhận';
  printDialog({title:T,sub:`Hợp đồng <b>${esc(c.ma)}</b> · ${esc(c.ho_ten)}`,previewPath:'/api/print/receipt.png',previewBody:body,printPath:'/api/print/receipt',printBody:body});
}
const DUP_KEYS=['bks','so_khung','so_may','cccd'];
let dups=[],dupT=0,dupSeq=0,hdOK=false,hdFilter='',hdQ='',hdOpen=0;
const dupVals=()=>{const o={};['bks','so_khung','so_may','cccd','ho_ten'].forEach(k=>o[k]=val(k));return o;};
const DUPL={bks:'biển số',so_khung:'số khung',so_may:'số máy'};
/* Gộp các dòng "trùng biển số / số khung / số máy" của CÙNG 1 hợp đồng thành 1 dòng cho gọn */
function dupLines(ws){
  const by=new Map(),rest=[];
  ws.forEach(w=>{const c=w.contract;
    if(c&&/_active$/.test(w.kind)&&DUPL[w.field]){const e=by.get(c.id)||{c,f:[]};e.f.push(DUPL[w.field]);by.set(c.id,e);}else rest.push(w.msg);});
  return [...by.values()].map(e=>`${e.c.ma} · trùng ${e.f.join(', ')} · hạn ${e.c.den_ngay_vn||'?'} · đang cầm, chưa chuộc`).concat(rest);
}
function dupView(){   // bỏ dòng "Khách này đang có HĐ…" khi hợp đồng đó đã nằm trong cảnh báo xe trùng
  const ids=new Set(dups.filter(w=>w.level==='high'&&w.contract).map(w=>w.contract.id));
  return dups.filter(w=>!(w.kind==='cccd_active'&&w.contract&&ids.has(w.contract.id)));
}
function paintDup(){
  const b=$('#dupBox');if(!b)return;
  const T={high:'Xe này đã có trong hệ thống',warn:'Cần kiểm tra',info:'Thông tin'};
  const IC='<svg class="dic" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l10 18H2zM12 10v5M12 18h.01"/></svg>';
  // Gộp "trùng" + "cần kiểm tra" thành 1 khung (mức cao nhất làm tiêu đề); "thông tin" để riêng
  const groups=[['high','warn'],['info']].map(ls=>dupView().filter(w=>ls.includes(w.level))).filter(g=>g.length);
  b.innerHTML=groups.map(g=>{const l=g.some(w=>w.level==='high')?'high':g[0].level;
    const cs=[...new Map(g.filter(w=>w.contract&&w.contract.id).map(w=>[w.contract.id,w.contract])).values()];
    const msgs=[...g].sort((x,y)=>(x.level==='high'?0:1)-(y.level==='high'?0:1));
    return `<div class="dup ${l}">${IC}<div class="dc"><b>${T[l]}</b>${dupLines(msgs).map(m=>`<div>${esc(m)}</div>`).join('')}${hdOK&&cs.length?`<div class="dgo">${cs.map(c=>`<button type="button" class="go" data-hd="${c.id}">Xem ${esc(c.ma||'hợp đồng')}</button>`).join('')}</div>`:''}</div></div>`;}).join('');
  document.querySelectorAll('#rvBody .rv').forEach(r=>r.classList.toggle('dupf',dups.some(w=>w.level!=='info'&&w.field===r.dataset.row)));
}
function dupCheck(now){
  clearTimeout(dupT);
  dupT=setTimeout(async()=>{
    const v=dupVals();if(!v.bks&&!v.so_khung&&!v.so_may&&!v.cccd){dups=[];paintDup();return;}
    const seq=++dupSeq;
    try{const r=await api('/api/contracts/check',{method:'POST',body:JSON.stringify(v)});if(seq===dupSeq){dups=r.warnings||[];paintDup();}}catch(e){}   // lỗi mạng: bỏ qua, không chặn làm hồ sơ
  },now?0:600);
}
$('#dupBox').addEventListener('click',e=>{const g=e.target.closest('[data-hd]');if(g)hdShow(+g.dataset.hd);});

