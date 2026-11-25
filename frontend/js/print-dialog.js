/* ================= Cài đặt in: in đè lên giấy mẫu có sẵn ================= */
const PS={overlay:true,dx:0,dy:0};
try{Object.assign(PS,JSON.parse(localStorage.getItem('printSet')||'{}'));}catch{}
const savePS=()=>{try{localStorage.setItem('printSet',JSON.stringify(PS));}catch{}};
const SAMPLE={ho_ten:'NGUYEN VAN A',dia_chi:'123 Duong ABC, P. 1, TP Phan Rang',cccd:'058200000000',sdt:'0900000000',ngay_cap:'15/03/2021',
  nhan_hieu:'HONDA',so_loai:'VISION',mau:'DO',bks:'85B1-123.45',so_khung:'RLHJK1403PZ123456',so_may:'JK14E1234567',le_phi:'50000',so_tien:'5000000',so_ngay:'30',tu_ngay:'19/11/2026',ngay_lap:'19/11/2026'};
/* Hộp thoại in riêng của app (không dùng hộp thoại in của trình duyệt): xem trước ảnh đúng như sẽ in, bấm In → máy chủ gửi thẳng máy in. */
async function printDialog({title,sub,previewPath,previewBody,printPath,printBody}){
  const hdr=()=>AU.tok?{'X-Session':AU.tok}:{};
  const post=(path,body)=>fetch(path,{method:'POST',headers:{'Content-Type':'application/json',...hdr()},body:body?JSON.stringify(body):undefined});
  openModal(`<h2>${esc(title)}</h2>${sub?`<p>${sub}</p>`:''}<div class="pvbox" id="pvBox"><span>Đang tạo bản xem trước…</span></div>
    <div class="pvst" id="pvSt" role="status"></div>
    <div class="stack"><button class="btn primary" id="pvGo" disabled>In</button><button class="btn link" id="pvX">Đóng</button></div>`);
  $('#pvX').onclick=closeModal;
  const st=(t,c='')=>{const e=$('#pvSt');if(e){e.className='pvst '+c;e.textContent=t;}};
  try{const r=await (previewBody?post(previewPath,previewBody):fetch(previewPath,{headers:hdr()}));
    if(!r.ok)throw new Error();const u=URL.createObjectURL(await r.blob());
    const b=$('#pvBox');if(b)b.innerHTML=`<img alt="Bản xem trước" src="${u}">`;}
  catch{const b=$('#pvBox');if(b)b.innerHTML='<span>Không tạo được bản xem trước</span>';}
  const go=$('#pvGo');if(!go)return;go.disabled=false;
  go.onclick=async()=>{go.disabled=true;go.textContent='Đang gửi…';st('Đang gửi lệnh in sang máy in…');
    try{const r=await post(printPath,printBody);const j=await r.json().catch(()=>({}));
      if(!r.ok)throw new Error(typeof j.detail==='string'?j.detail:'Không gửi được lệnh in');
      st('Đã gửi lệnh in tới máy in '+(j.printer||'')+'. Hãy kiểm tra giấy đã ra chưa.','ok');go.textContent='In lại';go.disabled=false;$('#pvX').textContent='Xong';}
    catch(e){st(e.message||'Không gửi được lệnh in','bad');go.textContent='Thử lại';go.disabled=false;}};
}
function printTest(){
  printDialog({title:'In thử',sub:'Bản in thử bằng dữ liệu mẫu, dùng để căn lề với giấy mẫu.',previewPath:'/api/print/test.png',printPath:'/api/print/test'});
}
$('#btnPrintSet').onclick=()=>{
  openModal(`<h2>Cài đặt in</h2><p style="text-align:left;margin-bottom:16px">
    <label class="switch"><input type="radio" name="pm" value="1" ${PS.overlay?'checked':''}> In đè lên giấy mẫu có sẵn (khuyên dùng)</label>
    <label class="switch"><input type="radio" name="pm" value="0" ${PS.overlay?'':'checked'}> In cả mẫu (dùng giấy trắng)</label></p>
    <div class="f"><div class="lab"><label for="px">Dịch sang phải (mm) — số âm là sang trái</label></div><input id="px" inputmode="decimal" value="${PS.dx}"></div>
    <div class="f"><div class="lab"><label for="py">Dịch xuống dưới (mm) — số âm là lên trên</label></div><input id="py" inputmode="decimal" value="${PS.dy}"></div>
    <p class="hint" style="text-align:left">Cách căn: bấm “In thử” ra giấy trắng, đặt chồng lên giấy mẫu rồi soi dưới ánh sáng. Chữ lệch bao nhiêu mm thì nhập vào đây.</p>
    <div class="stack"><button class="btn secondary" id="ps-test">In thử (giấy trắng, dữ liệu mẫu)</button><button class="btn primary" id="ps-ok">Lưu</button></div>`);
  const read=()=>{PS.overlay=document.querySelector('input[name=pm]:checked').value==='1';PS.dx=parseFloat($('#px').value.replace(',','.'))||0;PS.dy=parseFloat($('#py').value.replace(',','.'))||0;savePS();refresh();};
  $('#ps-ok').onclick=()=>{read();closeModal();};
  $('#ps-test').onclick=()=>{read();closeModal();printTest();};
};

