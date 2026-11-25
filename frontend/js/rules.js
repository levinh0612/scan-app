/* ===== Luật kiểm tra: muốn đổi luật chỉ sửa bảng RULES / POLICY này, phần giao diện không phụ thuộc =====
   lv:'block' = sai hẳn → ô đỏ, chưa cho sang bước sau.
   lv:'warn'  = đáng ngờ → ô vàng, vẫn cho đi tiếp sau khi người dùng xác nhận "giữ nguyên".
   bad(v) trả về true khi vi phạm; msg là chuỗi hoặc hàm(v). Ô bắt buộc để trống luôn bị chặn (cờ req ở FIELDS). */
const POLICY={confirmWarnings:true,          // true: có cảnh báo thì hỏi lại trước khi sang bước 3
              soTienMin:100000,soTienMax:500000000,soNgayMax:365,namCapMin:2012};
const digits=v=>v.replace(/[\s.\-]/g,'');
const RULES={
  ho_ten:[
    {lv:'block',bad:v=>!/^[\p{L}][\p{L}\s.'-]*$/u.test(v),msg:'Họ tên chỉ gồm chữ cái, không có số hay ký tự lạ'},
    {lv:'warn',bad:v=>v.split(/\s+/).length<2,msg:'Họ tên thường có ít nhất 2 chữ. Kiểm tra lại khoảng cách giữa các chữ'},
    {lv:'warn',bad:v=>!/[^\x00-\x7f]/.test(v),msg:'Chưa có dấu tiếng Việt — hãy soát và gõ lại nếu cần'},
  ],
  cccd:[
    {lv:'block',bad:v=>!/^\d{12}$/.test(v),msg:'Số CCCD phải đủ 12 chữ số'},
    {lv:'warn',bad:v=>{const p=+v.slice(0,3);return p<1||p>96;},msg:'Mã tỉnh ở 3 số đầu không hợp lệ — kiểm tra lại'},
  ],
  ngay_cap:[
    {lv:'block',bad:v=>!parseD(v),msg:'Ngày chưa đúng. Ví dụ: 15/03/2021'},
    {lv:'block',bad:v=>{const d=parseD(v);return d&&d>new Date();},msg:'Ngày cấp không thể ở tương lai'},
    {lv:'warn',bad:v=>{const d=parseD(v);return d&&d.getFullYear()<POLICY.namCapMin;},msg:'Ngày cấp quá cũ so với thẻ CCCD — so lại với giấy tờ'},
  ],
  sdt:[
    {lv:'block',bad:v=>!/^\d+$/.test(digits(v)),msg:'Số điện thoại chỉ gồm chữ số'},
    {lv:'block',bad:v=>digits(v)[0]!=='0',msg:'Số điện thoại phải bắt đầu bằng 0'},
    {lv:'block',bad:v=>!(/^0[35789]\d{8}$/.test(digits(v))||/^02\d{9}$/.test(digits(v))),
      msg:v=>digits(v).length<10?'Số điện thoại còn thiếu số (cần 10 số)':'Số điện thoại chưa đúng (di động 10 số, vd 0905123456)'},
  ],
  bks:[{lv:'warn',bad:v=>!/^\d{2}[A-Z]{1,2}\d?-?\d{3}\.?\d{1,2}$/.test(v.toUpperCase().replace(/\s/g,'')),msg:'Biển số chưa đúng khuôn dạng, vd 85B1-988.06'}],
  so_khung:[
    {lv:'warn',bad:v=>!/^[A-Za-z0-9]+$/.test(v),msg:'Chỉ gồm chữ và số, không có khoảng trắng hay ký tự lạ'},
    {lv:'warn',bad:v=>v.length<6||v.length>20,msg:'Độ dài bất thường (thường 8–17 ký tự) — soát từng ký tự'},
  ],
  tu_ngay:[{lv:'block',bad:v=>!parseD(v),msg:'Ngày chưa đúng. Ví dụ: 19/11/2026'}],
  so_tien:[
    {lv:'block',bad:v=>!(+v>0),msg:'Số tiền phải lớn hơn 0'},
    {lv:'warn',bad:v=>+v>0&&+v<POLICY.soTienMin,msg:v=>`Số tiền ${money(v)}đ nhỏ bất thường — có thiếu số 0 không?`},
    {lv:'warn',bad:v=>+v>POLICY.soTienMax,msg:v=>`Số tiền ${money(v)}đ rất lớn — kiểm tra lại số 0`},
  ],
  so_ngay:[
    {lv:'block',bad:v=>!(+v>0),msg:'Số ngày phải lớn hơn 0'},
    {lv:'warn',bad:v=>+v>POLICY.soNgayMax,msg:'Thời hạn trên 1 năm, bạn chắc chứ?'},
  ],
};
RULES.so_may=RULES.so_khung;
function validate(k,v){
  v=(v||'').toString().trim();
  if(!v)return FIELDS.find(f=>f.k===k)?.req?{status:'missing',note:'Chưa có thông tin — bấm vào ô để nhập'}:{status:'ok',note:''};
  let warn=null;
  for(const r of RULES[k]||[]){
    if(!r.bad(v))continue;
    const note=typeof r.msg==='function'?r.msg(v):r.msg;
    if(r.lv==='block')return{status:'missing',note};
    warn=warn||{status:'check',note};
  }
  return warn||{status:'ok',note:''};
}
const missingFields=()=>FIELDS.filter(f=>f.k&&f.req&&(!val(f.k)||validate(f.k,val(f.k)).status==='missing'));
const checkFields=()=>FIELDS.filter(f=>f.k&&val(f.k)&&state[f.k]?.status==='check');

