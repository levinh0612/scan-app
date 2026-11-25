/* ================= Trạng thái máy in (do máy chủ hỏi hệ điều hành) ================= */
const PRN_TXT={ready:'Máy in: đã kết nối',printing:'Máy in: đang in',offline:'Máy in: chưa kết nối',error:'Máy in: có lỗi',none:'Máy in: chưa cài',unknown:'Máy in: chưa kiểm tra được'};
const PRN_BOX={ready:'Máy in sẵn sàng',printing:'Đang in…',offline:'Máy in chưa kết nối',error:'Máy in có lỗi',none:'Chưa cài máy in',unknown:'Chưa kiểm tra được máy in'};
let prnInfo=null;
async function checkPrinter(){
  try{prnInfo=await api('/api/printer');}catch{prnInfo={status:'unknown',name:'',printers:[]};}
  const b=$('#btnPrn'),s=prnInfo.status;b.dataset.s=s;
  $('#prnLabel').textContent=PRN_TXT[s]||PRN_TXT.unknown;$('#prnLabel2').textContent=$('#prnLabel').textContent;$('#btnPrn2').dataset.s=s;
  $('#prnBox').dataset.s=s;$('#prnBoxT').textContent=PRN_BOX[s]||PRN_BOX.unknown;$('#prnBoxN').textContent=prnInfo.name?prnInfo.name.replace(/_+/g,' ').replace(/\s[0-9a-f]{8,}\s*$/i,'').trim()+' · A5':'';
  $('#btnQueue').dataset.s=s;$('#w3Prn').dataset.s=s;$('#w3PrnT').textContent=$('#prnBoxT').textContent;$('#w3PrnN').textContent=$('#prnBoxN').textContent;
  b.title=prnInfo.name?`Máy in: ${prnInfo.name}`:'';
}
$('#btnPrn').onclick=()=>{
  const i=prnInfo||{status:'unknown',printers:[]};
  const list=i.printers.map(p=>`• ${p.name}${p.default?' (mặc định)':''}`).join('<br>');
  const msg={ready:'Máy tính trong tiệm thấy máy in và máy in đang bật.',printing:'Máy in đang xử lý lệnh in.',
    offline:'Máy in đang tắt hoặc chưa nối với máy tính. Kiểm tra nguồn và dây cáp/Wi-Fi.',error:'Máy in báo lỗi. Kiểm tra giấy, kẹt giấy, đèn báo trên máy in.',
    none:'Máy tính trong tiệm chưa cài máy in nào. Cài driver máy in rồi thử lại.',unknown:'Chưa hỏi được máy tính trong tiệm (máy chủ có đang chạy không?).'}[i.status];
  openModal(`<div class="big ${i.status==='ready'||i.status==='printing'?'ok':'ask'}" aria-hidden="true">${i.status==='ready'||i.status==='printing'?ic('check'):ic('info')}</div><h2>${PRN_TXT[i.status]||PRN_TXT.unknown}</h2>
   <p>${msg}${list?'<br><br>'+list:''}<br><br><small>Chỉ biết máy in đã nối và bật, không biết còn giấy hay mực. Sau khi in, hãy xem giấy đã ra chưa.</small></p>
   <div class="stack"><button class="btn primary" id="m-x">Đã hiểu</button><button class="btn secondary" id="m-set">Cài đặt in &amp; căn chỉnh giấy mẫu</button><button class="btn link" id="m-re">Kiểm tra lại</button></div>`);
  $('#m-set').onclick=()=>{closeModal();$('#btnPrintSet').click();};
  $('#m-x').onclick=closeModal;$('#m-re').onclick=async()=>{await checkPrinter();closeModal();};
};

