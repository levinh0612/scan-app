/* --- Màn hình nhập PIN (điện thoại) --- */
function hdPin(after){
  hdOpenView('tabHd');
  const PL=()=>AU.pin_len||6;let pin='',busy=false,lock=AU.locked||0,tm=0;
  const upd=()=>{document.querySelectorAll('.pind i').forEach((d,i)=>d.classList.toggle('on',i<pin.length));const o=$('#pinOk');if(o)o.disabled=pin.length<4||lock>0;};
  const paint=()=>{
    if(!AU.pin_set){
      hdPaint(`<div class="pinw"><div class="pinic">${ic('lock')}</div><h2>Chưa đặt mã PIN</h2>
        <div class="pinno"><b>Làm 1 lần trên máy tính ở tiệm:</b><ol><li>Mở <b>Cài đặt</b></li><li>Mục <b>Mã PIN cho điện thoại</b> → nhập 4–6 số → <b>Đặt PIN</b></li><li>Quay lại điện thoại, kéo xuống để tải lại</li></ol></div>
        <button class="btn primary" id="pinOk" type="button">Tải lại</button><button class="btn link" id="pinBack" type="button">‹ Quay lại</button></div>`);
      $('#pinBack').onclick=hdClose;$('#pinOk').onclick=async()=>{await authInit();if(AU.authed)after();else paint();};return;
    }
    hdPaint(`<div class="pinw${AU.pin_len?' pauto':''}"><div class="pinic">${ic('lock')}</div><h2>Nhập mã PIN</h2><p class="pins">${lock>0?`Nhập sai nhiều lần. Thử lại sau <b>${Math.floor(lock/60)}:${pad(lock%60)}</b>.`:'Để xem hợp đồng trên điện thoại.'} </p>
      <div class="pind" aria-live="polite">${Array.from({length:PL()},(_,i)=>i).map(i=>`<i class="${i<pin.length?'on':''}"></i>`).join('')}<input id="pinIn" class="pinin" type="tel" inputmode="numeric" pattern="[0-9]*" maxlength="${PL()}" autocomplete="one-time-code" aria-label="Mã PIN" value="${pin}" ${lock>0?'disabled':''}></div><div class="pine" id="pinE"></div><button class="pinhint" id="pinTap" type="button">Chạm vào đây để nhập mã</button>
      ${AU.pin_len?'':`<button class="btn primary" id="pinOk" type="button" ${pin.length<4||lock>0?'disabled':''} >Mở khóa</button>`}
      <button class="btn link" id="pinBack" type="button">‹ Quay lại</button></div>`);
    $('#pinBack').onclick=hdClose;if($('#pinOk'))$('#pinOk').onclick=go;
    const inp=$('#pinIn');
    if(inp){
      /* iOS đôi khi không bắn 'input' (gợi ý, bộ gõ…): nghe nhiều sự kiện + dò giá trị định kỳ */
      const sync=()=>{if(busy||!document.body.contains(inp))return;const v=inp.value.replace(/\D/g,'').slice(0,PL());if(v===pin&&inp.value===v)return;pin=v;inp.value=v;upd();if(AU.pin_len&&pin.length===PL()&&lock<=0)go();};
      ['input','keyup','change','paste'].forEach(ev=>inp.addEventListener(ev,()=>setTimeout(sync,0)));
      clearInterval(inp._t);inp._t=setInterval(()=>{if(!document.body.contains(inp)){clearInterval(inp._t);return;}sync();},150);
      inp.onkeydown=e=>{if(e.key==='Enter'&&pin.length>=4&&lock<=0)go();};
      const foc=()=>{if(lock<=0){inp.focus({preventScroll:true});try{inp.setSelectionRange(inp.value.length,inp.value.length);}catch(e){}}};
      document.querySelectorAll('.pinw').forEach(w=>w.addEventListener('click',e=>{if(e.target.closest('#pinBack,#pinOk'))return;foc();}));
      foc();}
  };
  const go=async()=>{
    busy=true;
    try{const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin})});const j=await r.json().catch(()=>({}));
      if(r.ok){setTok(j.token);AU.authed=true;AU.t=Date.now();clearInterval(tm);after();return;}
      pin='';busy=false;
      if(r.status===429){lock=+r.headers.get('Retry-After')||300;AU.locked=lock;}
      paint();const e=$('#pinE');if(e)e.textContent=typeof j.detail==='string'?j.detail:'Không đăng nhập được.';
    }catch(e){busy=false;paint();$('#pinE').textContent='Mất kết nối với máy ở tiệm.';}
  };
  paint();
  clearInterval(tm);tm=setInterval(()=>{if($('#hdv').hidden||!$('#pinE')){clearInterval(tm);return;}if(lock>0){lock--;AU.locked=lock;if(lock%5===0||lock===0)paint();}},1000);
}
async function needAuth(next){await authInit();if(AU.authed)return next();hdPin(next);}

