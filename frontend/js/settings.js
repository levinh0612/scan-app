/* --- Cài đặt (chỉ máy tính ở tiệm) --- */
async function hdSettings(page){
  hdOpenView('tabSt');
  await authInit();if(!AU.local){hdClose();toast('Cài đặt chỉ mở được trên máy tính ở tiệm.');return;}
  let s,b;try{[s,b]=await Promise.all([api('/api/settings'),api('/api/contracts/backups')]);}catch(e){hdPaint('<div class="empty"><div>'+ic('warn')+'</div><b>Không tải được cài đặt</b></div>');return;}
  DEF=s;
  if(matchMedia('(max-width:999px)').matches)return stPhone(s,b,typeof page==='string'?page:'');
  hdPaint(`<div class="hdtop"><h2>Cài đặt</h2></div>
  <div class="grp row"><div><h4>Kết nối điện thoại</h4><p class="hdnote">Quét mã QR để mở app trên điện thoại.</p></div><button class="btn secondary sm" id="sLink" type="button">Hiện mã QR</button></div>
  <div class="grp setdef"><h4>Mặc định khi lập / gia hạn ${qh('ngay')}</h4>
    <label class="fl">Số ngày mỗi kỳ<input id="sNgay" inputmode="numeric" value="${s.so_ngay_ky}"></label>
    <label class="fl">Lệ phí mỗi kỳ (đồng)<input id="sPhi" inputmode="numeric" value="${money(s.le_phi_ky)}"></label>
    <label class="fl">Giữ ảnh sau khi đóng hợp đồng (ngày) ${qh('anh')}<input id="sAnh" inputmode="numeric" value="${s.anh_giu_ngay}"></label>
    <button class="btn primary sm" id="sSave" type="button">Lưu cài đặt</button><div class="okmsg" id="sOk" hidden>${ic('check')} Đã lưu</div></div>
  <details class="grp fold"><summary><h4>Mã PIN cho điện thoại ${qh('pin')}</h4><span class="st">${s.pin_set?'Đã đặt':'Chưa đặt'}</span><i class="chev"></i></summary><p class="hdnote">${s.pin_set?'Đã đặt PIN. Đổi PIN sẽ đăng xuất mọi điện thoại.':'Chưa đặt PIN: điện thoại chưa xem được hợp đồng.'}</p>
    <label class="fl">${s.pin_set?'PIN mới':'Đặt PIN'} (4–6 số)<input id="sPin" type="password" inputmode="numeric" maxlength="6" autocomplete="new-password"></label>
    <button class="btn primary sm" id="sPinB" type="button">${s.pin_set?'Đổi PIN':'Đặt PIN'}</button><div class="okmsg" id="pOk" hidden>${ic('check')} Đã lưu PIN</div></details>
  <div class="grp"><h4>Sao lưu tự động</h4>${bkLine({sao_luu:s.sao_luu})}
    <details class="fold2"><summary>Bản sao lưu trong máy (${b.items.length})</summary><p class="hdnote">Mỗi ngày 1 bản, giữ 30 ngày.</p>
    ${b.items.length?b.items.map(x=>`<div class="ev"><b>${esc(x.name.replace('contracts-','').replace('.db',''))}</b><span>${esc(x.at)} · ${x.hop_dong} hợp đồng · ${x.kb}&nbsp;KB</span><button class="btn secondary sm" data-rs="${esc(x.name)}" type="button">Khôi phục</button></div>`).join(''):'<p class="hdev">Chưa có bản sao lưu.</p>'}</details></div>
  <details class="grp fold"><summary><h4>Ảnh giấy tờ ${qh('anh')}</h4><span class="st">${s.anh.so_anh} ảnh · ${s.anh.mb} MB</span><i class="chev"></i></summary><p class="hdnote">Đang lưu <b>${s.anh.so_anh}</b> ảnh, <b>${s.anh.mb}</b> MB trong thư mục <code>${esc(s.anh.thu_muc||'data/anh')}</code>. Ảnh tự xóa sau ${s.anh_giu_ngay} ngày kể từ khi hợp đồng đóng hoặc hủy.</p></details>
  <details class="grp fold"><summary><h4>Quy tắc tính tiền</h4><i class="chev"></i></summary><p class="hdnote" style="line-height:1.6">${HELP.quy}</p></details>`);
  moneyIn($('#sPhi'));$('#sLink').onclick=()=>$('#tabLink').click();
  $('#sSave').onclick=async()=>{try{DEF=await api('/api/settings',{method:'POST',body:JSON.stringify({so_ngay_ky:numOf('sNgay'),le_phi_ky:numOf('sPhi'),anh_giu_ngay:numOf('sAnh')})});const m=$('#sOk');m.hidden=false;setTimeout(()=>m.hidden=true,2500);}catch(e){toast(errMsg(e));}};
  $('#sPinB').onclick=async()=>{const v=($('#sPin').value||'').trim();if(!/^\d{4,6}$/.test(v)){toast('PIN gồm 4 đến 6 chữ số.');return;}try{await api('/api/auth/pin',{method:'POST',body:JSON.stringify({pin:v})});$('#sPin').value='';const m=$('#pOk');m.hidden=false;setTimeout(()=>{m.hidden=true;hdSettings();},1500);}catch(e){toast(errMsg(e));}};
  document.querySelectorAll('[data-rs]').forEach(x=>x.onclick=()=>fKhoiPhuc(x.dataset.rs));
}
function fKhoiPhuc(name){
  sheet(shHead('Khôi phục sao lưu')+`<div class="wn">Dữ liệu hiện tại sẽ được thay bằng bản <b>${esc(name.replace('contracts-','').replace('.db',''))}</b>. Trước khi khôi phục, app tự lưu lại bản hiện tại (không mất) để quay lại nếu cần. Hợp đồng lập sau ngày đó sẽ không còn trong danh sách.</div>${shErr}
  <div class="mact"><button class="btn secondary" data-x type="button">Hủy</button><button class="btn danger" id="fOk" type="button">Khôi phục</button></div>`,el=>{
    shBind(el);$('#fOk').onclick=async()=>{try{const r=await api('/api/contracts/restore',{method:'POST',body:JSON.stringify({name})});sheetX();toast('Đã khôi phục. Bản cũ được giữ: '+(r.giu_ban_cu||''));hdStatsRefresh();hdSettings();}catch(e){const m=$('#shErr');m.textContent=errMsg(e);m.hidden=false;}};
  });
}


/* --- Cài đặt trên điện thoại: danh sách mục, mỗi mục mở một trang riêng --- */
function stPhone(s,b,page){
  const IM={def:'info',pin:'lock',bk:'inbox',anh:'camera',quy:'check'};
  const L=(k,t,v,c)=>`<button type="button" class="strow" data-pg="${k}"><span class="sti ${c}">${ic(IM[k])}</span><span class="stt">${t}</span><span class="stv">${v||''}</span><i class="chev"></i></button>`;
  const back=t=>`<div class="stback"><button type="button" id="stBack">${ic('x')}<span>Cài đặt</span></button><h2>${t}</h2></div>`;
  const PG={
    def:['Mặc định khi lập / gia hạn',`<div class="grp setdef">
      <label class="fl">Số ngày mỗi kỳ<input id="sNgay" inputmode="numeric" value="${s.so_ngay_ky}"></label>
      <label class="fl">Lệ phí mỗi kỳ (đồng)<input id="sPhi" inputmode="numeric" value="${money(s.le_phi_ky)}"></label>
      <label class="fl">Giữ ảnh sau khi đóng hợp đồng (ngày)<input id="sAnh" inputmode="numeric" value="${s.anh_giu_ngay}"></label>
      <button class="btn primary sm" id="sSave" type="button">Lưu cài đặt</button><div class="okmsg" id="sOk" hidden>${ic('check')} Đã lưu</div></div><p class="hdnote">${qh('ngay')} Số ngày và lệ phí này được điền sẵn khi lập hoặc gia hạn hợp đồng.</p>`],
    pin:['Mã PIN',`<div class="pinpg"><div class="pinpgic">${ic('lock')}</div>
      <p class="pinpgt">${s.pin_set?'Điện thoại đang được khóa bằng PIN':'Chưa đặt PIN'}</p>
      <p class="pinpgs">${s.pin_set?'Đổi PIN sẽ đăng xuất mọi điện thoại đang mở.':'Đặt PIN để xem hợp đồng trên điện thoại.'}</p>
      <input id="sPin" class="pinfld" type="password" inputmode="numeric" maxlength="6" autocomplete="new-password" placeholder="${s.pin_set?'PIN mới':'Nhập PIN'}" aria-label="${s.pin_set?'PIN mới':'Đặt PIN'} 4 đến 6 số">
      <p class="pinpgh">4 đến 6 chữ số</p>
      <button class="btn primary" id="sPinB" type="button">${s.pin_set?'Đổi PIN':'Đặt PIN'}</button><div class="okmsg" id="pOk" hidden>${ic('check')} Đã lưu PIN</div></div>`],
    bk:['Sao lưu tự động',`<div class="grp">${bkLine({sao_luu:s.sao_luu})}</div><div class="grp"><p class="hdnote">Mỗi ngày 1 bản, giữ 30 ngày. Bản trong máy: ${b.items.length}.</p>
      ${b.items.length?b.items.map(x=>`<div class="ev"><b>${esc(x.name.replace('contracts-','').replace('.db',''))}</b><span>${esc(x.at)} · ${x.hop_dong} hợp đồng · ${x.kb}&nbsp;KB</span><button class="btn secondary sm" data-rs="${esc(x.name)}" type="button">Khôi phục</button></div>`).join(''):'<p class="hdev">Chưa có bản sao lưu.</p>'}</div>`],
    anh:['Ảnh giấy tờ',`<div class="grp"><p class="hdnote">Đang lưu <b>${s.anh.so_anh}</b> ảnh, <b>${s.anh.mb}</b> MB trong thư mục <code>${esc(s.anh.thu_muc||'data/anh')}</code>. Ảnh tự xóa sau ${s.anh_giu_ngay} ngày kể từ khi hợp đồng đóng hoặc hủy.</p></div>`],
    quy:['Quy tắc tính tiền',`<div class="grp"><p class="hdnote" style="line-height:1.6">${HELP.quy}</p></div>`],
  };
  if(PG[page]){
    hdPaint(back(PG[page][0])+PG[page][1]);
    $('#stBack').onclick=()=>hdSettings();
    if($('#sPhi'))moneyIn($('#sPhi'));
    const sv=$('#sSave');if(sv)sv.onclick=async()=>{try{DEF=await api('/api/settings',{method:'POST',body:JSON.stringify({so_ngay_ky:numOf('sNgay'),le_phi_ky:numOf('sPhi'),anh_giu_ngay:numOf('sAnh')})});const m=$('#sOk');m.hidden=false;setTimeout(()=>m.hidden=true,2500);}catch(e){toast(errMsg(e));}};
    const pb=$('#sPinB');if(pb)pb.onclick=async()=>{const v=($('#sPin').value||'').trim();if(!/^\d{4,6}$/.test(v)){toast('PIN gồm 4 đến 6 chữ số.');return;}try{await api('/api/auth/pin',{method:'POST',body:JSON.stringify({pin:v})});$('#sPin').value='';const m=$('#pOk');m.hidden=false;setTimeout(()=>{m.hidden=true;hdSettings('pin');},1500);}catch(e){toast(errMsg(e));}};
    document.querySelectorAll('[data-rs]').forEach(x=>x.onclick=()=>fKhoiPhuc(x.dataset.rs));
    return;
  }
  hdPaint(`<div class="hdtop"><h2>Cài đặt</h2></div>
  <div class="stlist"><button type="button" class="strow" id="sLink"><span class="sti c1">${ic('dots')}</span><span class="stt">Kết nối điện thoại</span><span class="stv">Mã QR</span><i class="chev"></i></button></div>
  <div class="stlist">${L('def','Mặc định lập / gia hạn',s.so_ngay_ky+' ngày','c2')}${L('pin','Mã PIN điện thoại',s.pin_set?'Đã đặt':'Chưa đặt','c3')}</div>
  <div class="stlist">${L('bk','Sao lưu tự động',b.items.length+' bản','c4')}${L('anh','Ảnh giấy tờ',s.anh.so_anh+' ảnh · '+s.anh.mb+' MB','c5')}${L('quy','Quy tắc tính tiền','','c6')}</div>`);
  $('#sLink').onclick=()=>$('#tabLink').click();
  document.querySelectorAll('[data-pg]').forEach(x=>x.onclick=()=>hdSettings(x.dataset.pg));
}
