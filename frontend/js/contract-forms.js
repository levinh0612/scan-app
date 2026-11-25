const crow=(l,v,cls='')=>`<div class="cr"><span>${l}</span><b class="${cls}">${v}</b></div>`;
function fRenew(c){
  const fee0=DEF.le_phi_ky||c.le_phi||0;
  sheet(shHead('Gia hạn','gh')+`<p class="shs">${esc(c.ma)} · ${esc(c.ho_ten)} · ${esc(c.bks)} · gốc ${money(c.so_tien)}đ · hạn hiện tại ${esc(c.den_ngay_vn)}</p>
  <div class="row2"><label class="fl">Số ngày<input id="fDays" inputmode="numeric" value="${DEF.so_ngay_ky||30}"></label>
  <label class="fl">Đến ngày<input id="fTo" type="date"></label></div>
  <label class="fl">Phí gia hạn thu thêm (đồng)<input id="fFee" inputmode="numeric" value="${fee0?money(fee0):''}" placeholder="0"></label>
  <label class="fl">Ghi chú<input id="fNote" placeholder="Không bắt buộc"></label>
  <div class="calc" id="fCalc"></div>${shErr}
  <div class="mact"><button class="btn secondary" data-x type="button">Hủy</button><button class="btn primary" id="fOk" type="button">Gia hạn</button></div>`,el=>{
    shBind(el);moneyIn($('#fFee'));
    const base=Math.max(parseISO(c.den_ngay).getTime(),new Date(new Date().toDateString()).getTime());
    const to=$('#fTo'),dd=$('#fDays');to.min=iso(new Date(base+86400000));
    const calc=()=>{const n=+numOf('fDays')||0;
      $('#fCalc').innerHTML=n>0?crow('Hạn mới',fmtD(new Date(base+n*86400000)),'em')+crow('Tiền gốc giữ nguyên',money(c.so_tien)+'đ')+crow('Phí tính vào doanh thu',money(+numOf('fFee')||0)+'đ')+`<small>${c.con_ngay<0?'Hợp đồng đã quá hạn nên đếm từ hôm nay.':'Nối tiếp từ hạn cũ.'}</small>`:'Nhập số ngày gia hạn.';};
    const dateFromDays=()=>{const n=+numOf('fDays')||0;to.value=n>0?iso(new Date(base+n*86400000)):'';};
    dd.addEventListener('input',()=>{dateFromDays();calc();});
    to.addEventListener('input',()=>{if(!to.value)return;const n=Math.round((parseISO(to.value).getTime()-base)/86400000);if(n>0){dd.value=n;calc();}});
    $('#fFee').addEventListener('input',calc);dateFromDays();calc();
    $('#fOk').onclick=()=>+numOf('fDays')>0?act(c.id,'renew',{days:numOf('fDays'),fee:numOf('fFee'),note:$('#fNote').value},'Đã gia hạn.'):($('#shErr').textContent='Nhập số ngày gia hạn.',$('#shErr').hidden=false);
  });
}
function fChuoc(c){
  sheet(shHead('Chuộc đồ','chuoc')+`<p class="shs">${esc(c.ma)} · ${esc(c.ho_ten)} · ${esc(c.bks)} · gốc ${money(c.so_tien)}đ</p>
  <label class="fl">Tổng số tiền khách trả (đồng)<input id="fAmt" inputmode="numeric" value="${money(c.so_tien)}"></label>
  <label class="fl">Ghi chú<input id="fNote" placeholder="Không bắt buộc"></label>
  <div class="calc" id="fCalc"></div>${shErr}
  <div class="mact"><button class="btn secondary" data-x type="button">Hủy</button><button class="btn primary" id="fOk" type="button">Khách chuộc đồ</button></div>`,el=>{
    shBind(el);moneyIn($('#fAmt'));
    const t=c.con_ngay==null?null:c.con_ngay>0?['sớm','early',`Chuộc sớm hạn (còn ${c.con_ngay} ngày, hạn ${esc(c.den_ngay_vn)})`]:c.con_ngay===0?['đúng','ontime',`Chuộc đúng hạn (hôm nay là hạn ${esc(c.den_ngay_vn)})`]:['trễ','late',`Chuộc trễ hạn (quá ${-c.con_ngay} ngày, hạn ${esc(c.den_ngay_vn)})`];
    const calc=()=>{const a=+numOf('fAmt')||0,f=Math.max(a-c.so_tien,0);
      $('#fCalc').innerHTML=(t?`<div class="tm ${t[1]}">${t[2]}</div>`:'')+crow('Thu hồi gốc',money(Math.min(a,c.so_tien))+'đ')+crow('Lệ phí thu thêm (doanh thu)',money(f)+'đ')+`<small>${a<c.so_tien?'Khách trả ít hơn tiền gốc, không có lệ phí.':'Tiền gốc nhận lại không tính là doanh thu.'}</small>`;};
    $('#fAmt').addEventListener('input',calc);calc();
    $('#fOk').onclick=()=>act(c.id,'chuoc',{amount:numOf('fAmt'),note:$('#fNote').value},'Đã ghi nhận khách chuộc đồ.');
  });
}
function fThanhLy(c){
  const som=c.con_ngay!=null&&c.con_ngay>=0;
  sheet(shHead('Thanh lý','tl_form')+`<p class="shs">${esc(c.ma)} · ${esc(c.ho_ten)} · ${esc(c.bks)} · gốc ${money(c.so_tien)}đ</p>
  ${som?`<div class="wn">${ic('warn')}Hợp đồng chưa quá hạn (${c.con_ngay===0?'đến hạn hôm nay':'còn '+c.con_ngay+' ngày'}). Vẫn thanh lý được, hãy chắc khách đã mất quyền chuộc.</div>`:''}
  <label class="fl">Giá bán thực tế (đồng)<input id="fAmt" inputmode="numeric" placeholder="Để trống nếu chưa bán"></label>
  <label class="fl">Ghi chú<input id="fNote" placeholder="Không bắt buộc"></label>
  <div class="calc" id="fCalc"></div>${shErr}
  <div class="mact"><button class="btn secondary" data-x type="button">Hủy</button><button class="btn primary" id="fOk" type="button">Thanh lý</button></div>`,el=>{
    shBind(el);moneyIn($('#fAmt'));
    const calc=()=>{const a=+numOf('fAmt')||0;
      $('#fCalc').innerHTML=a>0?`${a>=c.so_tien?'Lãi':'Lỗ'} thanh lý: <b class="${a>=c.so_tien?'gain':'loss'}">${a>=c.so_tien?'+':'−'}${money(Math.abs(a-c.so_tien))}đ</b><small>= giá bán ${money(a)}đ − gốc ${money(c.so_tien)}đ. Tiệm giữ lãi, chịu lỗ.</small>`:'Chưa nhập giá bán nên chưa tính lãi/lỗ vào báo cáo.';};
    $('#fAmt').addEventListener('input',calc);calc();
    $('#fOk').onclick=()=>act(c.id,'thanh_ly',{amount:numOf('fAmt'),note:$('#fNote').value},'Đã thanh lý.');
  });
}
function fNhac(c){
  sheet(shHead('Nhắn nhắc hạn')+`<p class="shs">Tin soạn sẵn cho ${esc(c.ho_ten)}. Sửa tùy ý trước khi gửi.</p><textarea class="hdmsg" id="rmMsg" aria-label="Nội dung tin nhắn">${esc(remindText(c))}</textarea>
  <div class="mact wrap"><button class="btn secondary" id="rmCopy" type="button">Sao chép</button><button class="btn secondary" id="rmZalo" type="button">Mở Zalo</button><a class="btn secondary" id="rmSms" href="#">Gửi SMS</a></div>`,el=>{
    shBind(el);const msg=()=>$('#rmMsg').value;
    $('#rmCopy').onclick=async()=>{try{await navigator.clipboard.writeText(msg());toast('Đã sao chép tin nhắn.');}catch(e){$('#rmMsg').select();toast('Hãy bấm giữ và sao chép tin nhắn.');}};
    $('#rmZalo').onclick=async()=>{try{await navigator.clipboard.writeText(msg());}catch(e){}toast('Đã chép tin nhắn — dán vào Zalo.');window.open('https://zalo.me/'+phone84(c.sdt),'_blank','noopener');};
    $('#rmSms').onclick=e=>{e.preventDefault();location.href='sms:'+String(c.sdt||'').replace(/\D/g,'')+'?&body='+encodeURIComponent(msg());};
  });
}
