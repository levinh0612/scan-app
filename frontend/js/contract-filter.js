/* Bộ lọc trạng thái hợp đồng: chọn nhiều (hdFilter là chuỗi các trạng thái, cách nhau dấu phẩy) */
const hdSet=()=>new Set(hdFilter.split(',').filter(Boolean));
const hdOpts=()=>FILTERS.filter(f=>f[0]&&(AU.local||f[0]!=='huy'));
function hdFltLabel(){
  const s=hdSet();if(!s.size)return 'Tất cả trạng thái';
  const n=hdOpts().filter(f=>s.has(f[0])).map(f=>f[1]);
  return n.length<=2?n.join(', '):n.length+' trạng thái';
}
function hdFltHtml(){
  return `<div class="flt"><button type="button" class="fbtn" id="hdFlt" aria-haspopup="listbox" aria-expanded="false"><span id="hdFltL">${hdFltLabel()}</span><i class="chev"></i></button>
  <div class="fpop" id="hdFpop" role="listbox" aria-multiselectable="true" hidden>${hdOpts().map(f=>`<label><input type="checkbox" value="${f[0]}"${hdSet().has(f[0])?' checked':''}><span class="bdg sm ${f[0]}">${f[1]}</span></label>`).join('')}<button type="button" class="fclr" id="hdFclr">Bỏ chọn tất cả</button></div></div>`;
}
function hdFltSync(){   // cập nhật nhãn, ô chọn, thẻ số liệu rồi tải lại danh sách (không vẽ lại cả trang)
  const s=hdSet();
  $('#hdFltL').textContent=hdFltLabel();
  document.querySelectorAll('#hdFpop input').forEach(i=>i.checked=s.has(i.value));
  document.querySelectorAll('.hdst [data-f]').forEach(b=>b.classList.toggle('on',s.size===1&&s.has(b.dataset.f)));
  hdList();
}
function hdFltBind(){
  const pop=$('#hdFpop'),btn=$('#hdFlt');
  const shut=()=>{pop.hidden=true;btn.setAttribute('aria-expanded','false');};
  btn.onclick=e=>{e.stopPropagation();pop.hidden=!pop.hidden;btn.setAttribute('aria-expanded',String(!pop.hidden));};
  pop.onclick=e=>e.stopPropagation();
  pop.onchange=()=>{hdFilter=[...pop.querySelectorAll('input:checked')].map(i=>i.value).join(',');hdFltSync();};
  $('#hdFclr').onclick=()=>{hdFilter='';hdFltSync();shut();};
  document.addEventListener('click',shut);
  document.querySelectorAll('.hdst [data-f]').forEach(b=>b.onclick=()=>{hdFilter=hdSet().size===1&&hdSet().has(b.dataset.f)?'':b.dataset.f;hdFltSync();});
}
