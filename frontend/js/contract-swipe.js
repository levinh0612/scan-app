/* Danh sách hợp đồng (điện thoại): vuốt dòng sang trái để hiện nút thao tác nhanh */
let hdQuiet=false;   // thao tác nhanh từ danh sách: xong thì ở lại danh sách, không mở chi tiết
const hdPhone=()=>matchMedia('(max-width:999px)').matches;
async function hdQuick(id,a){
  let d;
  try{d=await api('/api/contracts/'+id);}
  catch(e){if(e.status===401){hdPin(()=>hdQuick(id,a));return;}toast('Không mở được hợp đồng.');return;}
  hdQuiet=a!=='inlai';
  ({renew:fRenew,chuoc:fChuoc,nhac:fNhac,inlai:c=>fInLai(c,d.events)})[a](d.contract);
}
function hdSwipeBind(box){
  const rows=[...box.querySelectorAll('.hdsw')];let openRow=null;
  const set=(w,x,anim)=>{const r=w.querySelector('.hdrow');r.style.transition=anim?'transform .22s ease':'none';r.style.transform=x?`translateX(${x}px)`:'';};
  const close=w=>{if(!w)return;set(w,0,true);w.classList.remove('open');if(openRow===w)openRow=null;};
  rows.forEach(w=>{
    const r=w.querySelector('.hdrow'),W=w.querySelector('.hdact').offsetWidth||216;
    let x0=0,y0=0,base=0,dx=0,mode='';
    r.addEventListener('touchstart',e=>{if(!hdPhone())return;const t=e.touches[0];x0=t.clientX;y0=t.clientY;base=w.classList.contains('open')?-W:0;dx=base;mode='';},{passive:true});
    r.addEventListener('touchmove',e=>{if(!hdPhone()||!e.touches.length)return;const t=e.touches[0],mx=t.clientX-x0,my=t.clientY-y0;
      if(!mode){if(Math.abs(mx)<8&&Math.abs(my)<8)return;mode=Math.abs(mx)>Math.abs(my)?'h':'v';if(mode==='h'&&openRow&&openRow!==w)close(openRow);}
      if(mode!=='h')return;e.preventDefault();dx=Math.max(-W-24,Math.min(0,base+mx));set(w,dx,false);},{passive:false});
    r.addEventListener('touchend',()=>{if(mode!=='h')return;const op=dx<-W/2;set(w,op?-W:0,true);w.classList.toggle('open',op);openRow=op?w:(openRow===w?null:openRow);r.dataset.sw='1';setTimeout(()=>delete r.dataset.sw,350);});
    r.addEventListener('click',e=>{if(r.dataset.sw||w.classList.contains('open')){e.stopImmediatePropagation();e.preventDefault();if(!r.dataset.sw)close(w);}},true);
    w.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{close(w);hdQuick(+r.dataset.id,b.dataset.q);});
  });
  document.addEventListener('touchstart',e=>{if(openRow&&!openRow.contains(e.target))close(openRow);},{passive:true});
}
