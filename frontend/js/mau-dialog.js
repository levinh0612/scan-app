const MAU_CHIPS=[['Đen','#1c1c1e'],['Trắng','#fff'],['Đỏ','#e53935'],['Xanh','#1e6fd9'],['Vàng','#f5c518'],['Bạc','#c7c9cc'],['Xám','#8e8e93'],['Nâu','#8b5a2b'],['Hồng','#f48fb1'],['Cam','#fb8c00'],['Tím','#8e44ad'],['Ghi','#6b7280']];
document.body.insertAdjacentHTML('beforeend',`<div id="mauDlg" class="mdlg" hidden role="dialog" aria-modal="true" aria-labelledby="mauT"><div class="mcard"><h3 id="mauT">Chọn màu sơn</h3><p>Có thể chọn nhiều màu</p><div class="sw" id="sw">${MAU_CHIPS.map(([n,c])=>`<button type="button" data-c="${n}"><i style="background:${c}"></i>${n}</button>`).join('')}</div><div class="sw" id="swx"></div><div class="mother"><input id="mauOther" placeholder="Màu khác: gõ tên màu" autocomplete="off" enterkeyhint="done" aria-label="Màu khác"><button type="button" class="btn secondary" id="mauAdd">Thêm</button></div><div class="mact"><button type="button" class="btn secondary" id="mauClr">Xóa hết</button><button type="button" class="btn primary" id="mauOk">Xong</button></div></div></div>`);
function openMau(){paintSw();$('#mauDlg').hidden=false;}
function closeMau(){$('#mauDlg').hidden=true;}
function setMau(w){const v=w.join(' ');state.mau={value:v,...validate('mau',v),edited:true};document.querySelectorAll('[data-k="mau"]').forEach(i=>i.value=v);refresh();}
const MAU_MOD=/^(đậm|nhạt|lá|dương|chuối|ngọc|trơ)$/i;
const mauList=()=>{const o=[];for(const w of (val('mau')||'').split(/[\s,;/]+/).filter(Boolean)){if(o.length&&MAU_MOD.test(w))o[o.length-1]+=' '+w;else o.push(w);}return o;};   // tách theo dấu phẩy: 'Xanh lá' giữ nguyên
document.querySelectorAll('#sw button').forEach(b=>b.onclick=()=>{const w=mauList(),c=b.dataset.c,at=w.indexOf(c);if(at>=0)w.splice(at,1);else w.push(c);setMau(w);paintSw();});
function addMau(){const t=$('#mauOther'),v=t.value.trim().replace(/[,;]+/g,' ');if(!v)return;const w=mauList();if(!w.some(x=>x.toLowerCase()===v.toLowerCase()))w.push(v.charAt(0).toUpperCase()+v.slice(1));setMau(w);t.value='';paintSw();}
$('#mauAdd').onclick=addMau;$('#mauOther').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();addMau();}});
$('#mauOk').onclick=()=>{addMau();closeMau();};$('#mauClr').onclick=()=>{setMau([]);paintSw();};
$('#mauDlg').addEventListener('click',e=>{if(e.target.id==='mauDlg')closeMau();});
addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#mauDlg').hidden)closeMau();});
