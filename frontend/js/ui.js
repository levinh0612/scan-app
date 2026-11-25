/* --- Tiện ích giao diện --- */
var DEF={so_ngay_ky:30,le_phi_ky:0};
const numOf=id=>(($('#'+id)||{}).value||'').replace(/\D/g,'');
const iso=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
const moneyIn=el=>el&&el.addEventListener('input',()=>{const v=el.value.replace(/\D/g,'');el.value=v?money(v):'';});
function sheet(html,mount){
  let d=$('#sheet');
  if(!d){d=document.createElement('div');d.id='sheet';d.className='mdlg';d.setAttribute('role','dialog');d.setAttribute('aria-modal','true');document.body.appendChild(d);d.addEventListener('mousedown',e=>{if(e.target===d)sheetX();});}
  d.innerHTML=`<div class="sh">${html}</div>`;d.hidden=false;if(mount)mount(d.firstChild);
  const f=d.querySelector('input:not([type=hidden]),textarea');if(f)setTimeout(()=>f.focus(),60);
}
function sheetX(){const d=$('#sheet');if(d)d.hidden=true;}
document.addEventListener('keydown',e=>{if(e.key==='Escape')sheetX();});
const shHead=(t,k)=>`<div class="shh"><h3>${t}</h3>${k?qh(k):''}<button type="button" class="shx" data-x aria-label="Đóng">${ic('x')}</button></div>`;
const shBind=el=>el.querySelectorAll('[data-x]').forEach(b=>b.onclick=sheetX);
const errMsg=e=>(e&&e.message&&!/^\d+$/.test(e.message))?e.message:'Không thực hiện được, thử lại.';
function setTab(id){['tabHome','btnQueue','tabHd','tabRp','tabSt'].forEach(t=>{const e=$('#'+t);if(e)e.classList.toggle('on',t===id);});}
/* Thanh chuyển Hợp đồng ⇄ Báo cáo (chỉ hiện trên điện thoại, và chỉ khi có quyền xem báo cáo) */
function hdSeg(){return '';}   // điện thoại đã có tab Báo cáo riêng nên bỏ thanh chuyển
function hdOpenView(tab){closeQueue();$('#hdv').hidden=false;document.body.style.overflow='hidden';setTab(tab);}
const hdPaint=h=>{$('#hdIn').innerHTML=h;$('#hdv').scrollTop=0;};

