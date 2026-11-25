/* Chụp xong: đứng hình, hiện các giá trị đã đọc để soát/sửa ngay trong camera, bấm "Tiếp tục" mới lưu ảnh */
let camHold=null;const camFix={};   // camHold: ảnh vừa chụp đang chờ xem lại; camFix[kiểu giấy]: ô đã sửa tay / đã xác nhận trong camera
async function snap(how){
  if(snapping||camHold)return;snapping=true;
  const k=camKey;tr('snap',{kind:k,how:how==='auto'?'auto':'manual',sec:Math.round((Date.now()-camT0)/1000),peeks:peekN,read:Object.keys(peekAcc).length});peekStop();countStop();      // dừng xem trước ngay: yêu cầu xem trước đang chạy làm máy chủ bận → chụp bị trễ
  try{
    // loạt 4 khung liên tiếp (~0,2 giây, giữ yên máy): máy chủ chọn khung nét nhất rồi gộp để giảm nhiễu/mờ do rung tay
    const blobs=[];
    for(let i=0;i<4;i++){
      const c=cropFrame();if(!c)break;
      blobs.push(await new Promise(r=>c.toBlob(r,'image/jpeg',.92)));
      if(i<3)await new Promise(r=>setTimeout(r,50));
    }
    if(!blobs.length||!blobs[0])return;
    camHold={k,blobs,rows:[],edit:-1};camReview();
  }finally{snapping=false;}
}
function camReview(){
  const f=peekMerged(),keys=[...(PEEK_EXPECT[camHold.k]||[])];Object.keys(f).forEach(x=>{if(!keys.includes(x))keys.push(x);});
  camHold.rows=keys.map(key=>({key,v:f[key]?f[key].value:'',st:f[key]?f[key].status:'bad',ed:false}));
  $('#cam').dataset.rv='1';$('#camVideo').pause();$('#camFrame').dataset.s='ok';
  $('#camHint').textContent='Soát lại, chạm vào giá trị nếu cần sửa';
  camRvPaint();$('#camLive').hidden=false;
}
function camRvPaint(){
  const h=camHold;if(!h)return;
  $('#camLive').innerHTML=`<div class="q ${h.rows.some(r=>!r.v)?'no':'ok'}">${h.rows.some(r=>!r.v)?'Có ô chưa đọc được, chạm để nhập (hoặc nhập sau)':'Đã đọc xong. Chỉnh sửa nếu cần'}</div>`+h.rows.map((r,i)=>{
    const cls=r.ed?'ed':!r.v?'bad':r.st==='ok'?'ok':'chk';
    return `<div class="r ${cls}" data-i="${i}"><span>${PEEK_NAMES[r.key]||r.key}</span>${h.edit===i?`<input class="rin" value="${esc(r.v)}" autocomplete="off" autocapitalize="off">`:`<b>${r.v?esc(r.v):'Chưa đọc được'}</b>`}</div>`;}).join('');
  const inp=$('#camLive input');if(inp){inp.focus();inp.select();
    const done=()=>{if(!camHold||camHold.edit!==+inp.closest('.r').dataset.i)return;const r=h.rows[h.edit],v=inp.value.trim();h.edit=-1;if(v!==r.v){r.v=v;r.ed=!!v;}camRvPaint();};
    inp.onblur=done;inp.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();inp.blur();}};}
}
$('#camLive').addEventListener('click',e=>{const r=e.target.closest('.r');if(!camHold||!r||e.target.closest('input'))return;camHold.edit=+r.dataset.i;camRvPaint();});
$('#camRetake').onclick=()=>{const k=camHold.k;camHold=null;delete $('#cam').dataset.rv;camShow(k);$('#camVideo').play();peekLoop();};
$('#camCont').onclick=()=>{
  const h=camHold;if(!h)return;if(h.edit>=0)$('#camLive input')?.blur();
  camFix[h.k]={ed:{},ok:{},all:{},cam:true};h.rows.forEach(r=>{if(r.v){(r.ed?camFix[h.k].ed:camFix[h.k].ok)[r.key]=r.v;camFix[h.k].all[r.key]={v:r.v,st:r.ed?'ok':r.st};}});
  camHold=null;delete $('#cam').dataset.rv;commitShot(h.k,h.blobs);
};
async function commitShot(k,blobs){
  closeCam();      // đóng camera NGAY, ghép ảnh chạy nền
  stacking++;setFile(k,new File([blobs[0]],k+'.jpg',{type:'image/jpeg'}),true);
  if(k==='cccd_back'&&!files.cavet)setTimeout(()=>openCam('cavet'),350);          // chuyển thẳng sang chụp cà vẹt
  else if(k==='cavet'&&!files.cccd_back)setTimeout(()=>openCam('cccd_back'),350);
  let out=blobs[0];
  if(blobs.length>1){
    try{const fd=new FormData();blobs.forEach((b,i)=>fd.append('images',b,'f'+i+'.jpg'));
      const r=await fetch('/api/stack',{method:'POST',body:fd});if(r.ok)out=await r.blob();}catch(e){}   // lỗi mạng → dùng khung đầu
  }
  files[k]=new File([out],k+'.jpg',{type:'image/jpeg'});
  paintRvImgs();
  stacking--;maybeScan();
}
/* Sau khi máy chủ đọc xong: ô sửa tay trong camera đè lên kết quả; ô đã soát trong camera và còn khớp thì coi là đã xác nhận */
function applyCamFix(){
  const setEd=(k,v)=>{if(k in state)state[k]={value:v,...validate(k,v),edited:true};};
  const same=(a,b)=>(a||'').trim().toUpperCase()===(b||'').trim().toUpperCase();
  for(const fx of Object.values(camFix)){
    for(const[k,v]of Object.entries(fx.ed)){
      if(k==='nhan_hieu'){const[a,...b]=v.split(/\s+-\s+/);setEd('nhan_hieu',a);if(b.length)setEd('so_loai',b.join(' - '));}else setEd(k,v);}
    for(const[k,v]of Object.entries(fx.ok)){
      const cur=k==='nhan_hieu'?[val('nhan_hieu'),val('so_loai')].filter(Boolean).join(' - '):val(k),s=state[k];
      if(s&&s.status==='check'&&same(cur,v)){state[k]={...s,status:'ok',note:''};if(k==='nhan_hieu'&&state.so_loai&&state.so_loai.status==='check')state.so_loai={...state.so_loai,status:'ok',note:''};}
    }
  }
}
