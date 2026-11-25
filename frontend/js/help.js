/* ================= Hợp đồng · Báo cáo · Cài đặt · PIN ================= */
const HD_ST={dang_cam:'Đang cầm',sap_han:'Sắp đến hạn',qua_han:'Quá hạn',da_chuoc:'Đã chuộc',thanh_ly:'Thanh lý',huy:'Đã hủy'};
const bdg=c=>`<span class="bdg ${c.hien_thi}">${HD_ST[c.hien_thi]||c.hien_thi}${c.status==='dang_cam'&&c.con_ngay!=null?(c.con_ngay<0?` ${-c.con_ngay} ngày`:c.con_ngay<=3?` còn ${c.con_ngay} ngày`:''):''}</span>`;

/* --- Các quy tắc nghiệp vụ: hiện trong nút "?" --- */
const HELP={
  quy:`<b>Tổng quan quy tắc tính tiền</b><br>• <b>Vốn đang bỏ ra</b> = tổng tiền cầm (gốc) của các hợp đồng đang cầm.<br>• <b>Doanh thu</b> = lệ phí lúc cầm + phí gia hạn + phần khách trả thêm trên gốc khi chuộc.<br>• Chuộc: khách trả lại tiền gốc là <b>thu hồi vốn</b>, không phải doanh thu.<br>• <b>Lợi nhuận</b> = doanh thu + lãi/lỗ thanh lý.<br>• Hợp đồng đã <b>hủy</b> không nằm trong bất kỳ con số nào.`,
  von:`<b>Vốn đang bỏ ra</b>: tổng tiền cầm (gốc) của các hợp đồng <b>đang cầm</b> ngay lúc này. Hợp đồng đã chuộc, thanh lý hoặc hủy không còn tính. Không phụ thuộc kỳ báo cáo.`,
  dt:`<b>Doanh thu</b> trong kỳ gồm 3 khoản:<br>1) Lệ phí thỏa thuận lúc lập hợp đồng (theo ngày lập).<br>2) Phí gia hạn (theo ngày thu).<br>3) Phần khách trả thêm trên gốc khi chuộc (theo ngày chuộc).<br>Tiền gốc nhận lại <b>không</b> phải doanh thu.`,
  ln:`<b>Lợi nhuận</b> = doanh thu + lãi/lỗ thanh lý. Lãi/lỗ thanh lý = giá bán − tiền gốc (theo ngày thanh lý). Thanh lý chưa nhập giá bán thì chưa tính.`,
  ts:`<b>Tỷ suất</b> = lợi nhuận của kỳ ÷ vốn đang bỏ ra hiện tại. Chỉ để tham khảo nhanh mức sinh lời.`,
  thu_hoi:`<b>Thu hồi gốc</b>: khi khách chuộc, số tiền gốc quay về là vốn được trả lại, không tính vào doanh thu hay lợi nhuận.`,
  tl:`<b>Lãi/lỗ thanh lý</b> = giá bán − tiền gốc. Tiệm giữ phần lãi và chịu phần lỗ, theo đúng mẫu hợp đồng giấy. Giá bán 0 hoặc để trống = chưa tính.`,
  huy_:`<b>Hợp đồng đã hủy</b> (nhập nhầm) bị loại khỏi danh sách, mọi con số và cảnh báo trùng. Hủy phải ghi lý do và không mở lại được. Nếu chỉ bấm nhầm chuộc/thanh lý thì dùng “Mở lại”.`,
  xoa:`<b>Xóa hẳn</b> dùng để dọn hồ sơ thử nghiệm: xóa hợp đồng, lịch sử và ảnh khỏi máy. Khác với “Hủy” (vẫn lưu vết). Chỉ máy tính ở tiệm mới thấy nút này. Database được sao lưu trước khi xóa.`,
  gh:`<b>Gia hạn</b>: hạn mới = <b>ngày lớn hơn</b> giữa hạn cũ và hôm nay, cộng thêm số ngày gia hạn. Hợp đồng đã quá hạn thì đếm từ <b>hôm nay</b> (vd hạn 15/11, hôm nay 21/11, +30 ngày → 21/12). Tiền gốc không đổi. Có thể nhập số ngày hoặc chọn thẳng <b>ngày gia hạn đến</b>, hai ô tự khớp nhau. Phí gia hạn nhập tay (mặc định lấy từ Cài đặt) và tính vào doanh thu.`,
  chuoc:`<b>Chuộc đồ</b>: nhập <b>tổng số tiền khách trả</b> (mặc định bằng tiền gốc). Phần vượt quá gốc là lệ phí, tính vào doanh thu. Tiền gốc quay về chỉ là thu hồi vốn. Hệ thống ghi chú khách chuộc <b>sớm hạn</b> (trước ngày hạn), <b>đúng hạn</b> (đúng ngày hạn) hay <b>trễ hạn</b> (sau ngày hạn) để bạn đối chiếu; không tự thu thêm phí.`,
  tl_form:`<b>Thanh lý</b>: nhập giá bán thực tế. Lãi/lỗ = giá bán − tiền gốc, tính theo ngày thanh lý. Thanh lý sớm hơn hạn chỉ cảnh báo, không chặn. Bấm nhầm thì dùng “Mở lại”.`,
  mo_lai:`<b>Mở lại</b>: đưa hợp đồng đã chuộc/thanh lý về trạng thái đang cầm. Số liệu báo cáo tính theo trạng thái hiện tại, nên mở lại sẽ bỏ khoản chuộc/thanh lý đó khỏi báo cáo.`,
  sua:`<b>Sửa</b> cho phép chỉnh thông tin khách, xe, tiền gốc và lệ phí. Mọi lần sửa được ghi vào lịch sử (giá trị cũ → mới). Tiền gốc đổi thì vốn và lãi/lỗ thanh lý đổi theo.`,
  pin:`Điện thoại mở Hợp đồng phải nhập <b>PIN</b>. Sau PIN: xem danh sách, chi tiết, ảnh; gia hạn, chuộc, thanh lý, ghi chú. <b>Không</b> xem được tiền vốn/báo cáo, sao lưu, cài đặt, sửa/hủy/mở lại. Tự khóa sau 5 phút không dùng. Sai 5 lần thì khóa 5 phút.`,
  sl:`<b>Sao lưu tự động</b>: app tự lưu 1 bản mỗi ngày trong máy, giữ 30 ngày. Nhờ đó cứu được khi sửa nhầm hoặc xóa nhầm (bấm <b>Khôi phục</b> ở danh sách bản lưu).<br>Nếu máy hỏng hoặc mất thì bản lưu trong máy cũng mất. Để an toàn hơn, thỉnh thoảng bấm <b>Tải bản sao lưu về máy</b> rồi cất vào USB hoặc Google Drive.`,
  anh:`<b>Ảnh giấy tờ</b> lưu thành file trong thư mục <code>data/anh</code> (đã nén, không nằm trong database), tự xóa sau số ngày đã đặt kể từ khi hợp đồng đóng hoặc hủy. Ảnh không được chép lên Google Drive.`,
  ngay:`<b>Mặc định</b> số ngày và lệ phí mỗi kỳ được điền sẵn khi lập hợp đồng mới và khi gia hạn. Vẫn sửa được từng hợp đồng.`,
};
const qh=k=>`<details class="qh"><summary aria-label="Hướng dẫn">?</summary><div>${HELP[k]||''}</div></details>`;
document.addEventListener('click',e=>{document.querySelectorAll('details.qh[open]').forEach(d=>{if(!d.contains(e.target))d.open=false;});});

/* Giữ khung giải thích nằm gọn trong màn hình: dịch sang trái nếu tràn mép phải, sang phải nếu tràn mép trái. */
document.addEventListener('toggle',e=>{
  const d=e.target;if(!d.matches||!d.matches('details.qh')||!d.open)return;
  const p=d.querySelector('div');if(!p)return;
  p.style.left='0';p.style.transform='';
  const r=p.getBoundingClientRect(),W=document.documentElement.clientWidth,m=12;
  const dx=r.right>W-m?(W-m)-r.right:r.left<m?m-r.left:0;
  if(dx)p.style.transform=`translateX(${dx}px)`;
},true);
