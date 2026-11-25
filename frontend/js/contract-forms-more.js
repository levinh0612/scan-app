function fInLai(c,events){
  const list=events.filter(e=>['gia_han','chuoc','thanh_ly'].includes(e.type));
  sheet(shHead('In lại giấy tờ')+(list.length?`<p class="shs">Chọn biên nhận cần in lại.</p>`+list.map(e=>`<div class="ev"><b>${EV[e.type]}</b><span>${esc(e.at_vn)}${e.amount?' · '+money(e.amount)+'đ':''}</span><button class="btn secondary sm" data-rc="${e.id}" type="button">In</button></div>`).join(''):'<p class="shs">Hợp đồng chưa có biên nhận nào để in (chưa gia hạn, chuộc hay thanh lý).</p>')+`<div class="mact"><button class="btn secondary" data-x type="button">Đóng</button></div>`,el=>{
    shBind(el);el.querySelectorAll('[data-rc]').forEach(b=>b.onclick=()=>{sheetX();printReceipt(c,events.find(x=>x.id==b.dataset.rc));});
  });
}
function fNote(c){
  sheet(shHead('Ghi chú '+esc(c.ma))+`<textarea class="hdmsg" id="fNoteT" maxlength="500" placeholder="Ghi chú nội bộ (tối đa 500 ký tự)">${esc(c.note||'')}</textarea>${shErr}
  <div class="mact"><button class="btn secondary" data-x type="button">Hủy</button><button class="btn primary" id="fOk" type="button">Lưu</button></div>`,el=>{
    shBind(el);$('#fOk').onclick=()=>act(c.id,'note',{note:$('#fNoteT').value},'Đã lưu ghi chú.');
  });
}
const SUA_F=[['ho_ten','Họ tên'],['sdt','SĐT'],['cccd','CCCD'],['ngay_cap','Ngày cấp'],['dia_chi','Địa chỉ'],['bks','Biển số'],['nhan_hieu','Nhãn hiệu'],['so_loai','Số loại'],['mau','Màu sơn'],['so_khung','Số khung'],['so_may','Số máy'],['so_tien','Tiền gốc (đồng)'],['le_phi','Lệ phí (đồng)']];
function fSua(c){
  sheet(shHead('Sửa '+esc(c.ma),'sua')+`<div class="fgrid">${SUA_F.map(([k,l])=>`<label class="fl">${l}<input data-s="${k}" value="${esc(k==='so_tien'||k==='le_phi'?money(c[k]||0):c[k]||'')}" ${k==='so_tien'||k==='le_phi'?'inputmode="numeric"':''}></label>`).join('')}</div>${shErr}
  <div class="mact"><button class="btn secondary" data-x type="button">Hủy</button><button class="btn primary" id="fOk" type="button">Lưu thay đổi</button></div>`,el=>{
    shBind(el);el.querySelectorAll('[data-s=so_tien],[data-s=le_phi]').forEach(moneyIn);
    $('#fOk').onclick=()=>{const b={};el.querySelectorAll('[data-s]').forEach(i=>{const k=i.dataset.s;b[k]=(k==='so_tien'||k==='le_phi')?i.value.replace(/\D/g,''):i.value.trim();});act(c.id,'sua',b,'Đã lưu thay đổi.');};
  });
}
function fHuy(c){
  sheet(shHead('Hủy hợp đồng '+esc(c.ma),'huy_')+`<div class="wn">Chỉ dùng khi lập nhầm. Hợp đồng sẽ biến mất khỏi danh sách, báo cáo và cảnh báo trùng, và <b>không mở lại được</b>.</div>
  <label class="fl">Lý do hủy (bắt buộc)<input id="fWhy" placeholder="Vd: nhập nhầm biển số"></label>${shErr}
  <div class="mact"><button class="btn secondary" data-x type="button">Không hủy</button><button class="btn danger" id="fOk" type="button">Hủy hợp đồng</button></div>`,el=>{
    shBind(el);$('#fOk').onclick=()=>$('#fWhy').value.trim()?act(c.id,'huy',{reason:$('#fWhy').value.trim()},'Đã hủy hợp đồng.'):($('#shErr').textContent='Hãy nhập lý do hủy.',$('#shErr').hidden=false);
  });
}
function fXoa(c){
  sheet(shHead('Xóa hẳn '+esc(c.ma),'xoa')+`<div class="wn"><b>Xóa vĩnh viễn</b> hợp đồng, lịch sử và ảnh giấy tờ. Chỉ dùng khi thử nghiệm. Hệ thống tự sao lưu database trước khi xóa nhưng ảnh thì không khôi phục được.</div>
  <label class="fl">Gõ lại mã <b>${esc(c.ma)}</b> để xác nhận<input id="fCf" autocomplete="off" autocapitalize="characters" placeholder="${esc(c.ma)}"></label>${shErr}
  <div class="mact"><button class="btn secondary" data-x type="button">Không xóa</button><button class="btn danger" id="fOk" type="button">Xóa hẳn</button></div>`,el=>{
    shBind(el);$('#fOk').onclick=async()=>{
      const v=$('#fCf').value.trim();
      if(v.toUpperCase()!==c.ma.toUpperCase()){$('#shErr').textContent='Mã chưa khớp.';$('#shErr').hidden=false;return;}
      try{await api(`/api/contracts/${c.id}/xoa`,{method:'POST',body:JSON.stringify({confirm:c.ma})});sheetX();dlgX();toast('Đã xóa hẳn '+c.ma+'.');hdStatsRefresh();if($('#hdList'))hdList();dupCheck(true);}
      catch(e){$('#shErr').textContent=errMsg(e);$('#shErr').hidden=false;}
    };
  });
}
function fMoLai(c){
  sheet(shHead('Mở lại '+esc(c.ma),'mo_lai')+`<p class="shs">Đưa hợp đồng về trạng thái <b>đang cầm</b>. Khoản chuộc/thanh lý đã ghi sẽ bị bỏ khỏi báo cáo.</p>${shErr}
  <div class="mact"><button class="btn secondary" data-x type="button">Không</button><button class="btn primary" id="fOk" type="button">Mở lại</button></div>`,el=>{
    shBind(el);$('#fOk').onclick=()=>act(c.id,'reopen',{},'Đã mở lại hợp đồng.');
  });
}

