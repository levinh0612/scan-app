/* ================= Dữ liệu & kiểm tra ================= */
const FIELDS = [
  {g:'Người cầm đồ (theo CCCD)'},
  {k:'ho_ten',  l:'Họ và tên',        req:true},
  {k:'cccd',    l:'Số CCCD (12 số)',  req:true, mode:'numeric', max:12},
  {k:'ngay_cap',l:'Ngày cấp (ngày/tháng/năm)', req:true, ph:'vd 15/03/2021'},
  {k:'dia_chi', l:'Địa chỉ',          req:true, area:true},
  {k:'sdt',     l:'Số điện thoại',    req:true, mode:'tel'},
  {g:'Xe (theo cà vẹt)'},
  {k:'bks',      l:'Biển số',         req:true},
  {k:'nhan_hieu',l:'Nhãn hiệu', req:true},
  {k:'so_loai', l:'Số loại (model)'},
  {k:'so_khung', l:'Số khung',        req:true},
  {k:'so_may',   l:'Số máy',          req:true},
  {k:'mau',      l:'Màu sơn'},
  {g:'Giao dịch'},
  {k:'so_tien', l:'Số tiền cầm (đồng)', req:true, mode:'numeric'},
  {k:'le_phi',  l:'Lệ phí thỏa thuận (đồng)', mode:'numeric'},
  {k:'so_ngay', l:'Số ngày cầm',      req:true, mode:'numeric'},
  {k:'tu_ngay', l:'Từ ngày (ngày/tháng/năm)', req:true, ph:'vd 19/11/2026'},
];
const TAGS={ok:'Đã đọc',check:'Cần xem lại',missing:'Cần nhập'};
const state={}, files={};
const $=s=>document.querySelector(s);
const pad=n=>String(n).padStart(2,'0');
const fmtD=d=>`${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()}`;
const today=()=>fmtD(new Date());
const parseD=s=>{const m=/^(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})$/.exec((s||'').trim());if(!m)return null;const d=new Date(+m[3],+m[2]-1,+m[1]);return d.getMonth()===+m[2]-1?d:null;};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Địa chỉ: chỉ cho xuống dòng ở dấu phẩy ("Thôn 3", "Số nhà 43", "Đường Nguyễn Huệ" luôn đi liền nhau)
const addrH=s=>String(s??'').split(/\s*,\s*/).filter(Boolean).map(x=>`<span class="ad">${esc(x)}</span>`).join(', ');
const MAU={DEN:'Đen',TRANG:'Trắng',DO:'Đỏ',XANH:'Xanh',VANG:'Vàng',BAC:'Bạc',XAM:'Xám',NAU:'Nâu',HONG:'Hồng',CAM:'Cam',TIM:'Tím',GHI:'Ghi',LUC:'Lục',LAM:'Lam',DONG:'Đồng'};
const fixMau=v=>String(v||'').trim().split(/\s+/).map(w=>MAU[w.toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/Đ/g,'D')]||(w.charAt(0).toUpperCase()+w.slice(1).toLowerCase())).join(' ');
const money=n=>Number(n).toLocaleString('vi-VN');
const val=k=>(state[k]?.value||'').toString().trim();

const D=['không','một','hai','ba','bốn','năm','sáu','bảy','tám','chín'];
function read3(n,full){const t=Math.floor(n/100),c=Math.floor(n/10)%10,d=n%10,o=[];
  if(t||full)o.push(D[t]+' trăm');
  if(c>1)o.push(D[c]+' mươi');else if(c===1)o.push('mười');else if((t||full)&&d)o.push('lẻ');
  if(d){if(c>1&&d===1)o.push('mốt');else if(c>=1&&d===5)o.push('lăm');else if(c>1&&d===4)o.push('tư');else o.push(D[d]);}
  return o.join(' ');}
function words(n){if(n===0)return 'Không đồng';const U=['',' nghìn',' triệu',' tỷ'],g=[];
  while(n){g.push(n%1000);n=Math.floor(n/1000);}
  const p=[];for(let i=g.length-1;i>=0;i--){if(!g[i])continue;p.push(read3(g[i],i!==g.length-1)+U[i%4]);}
  const s=p.join(' ').trim()+' đồng';return s[0].toUpperCase()+s.slice(1);}

