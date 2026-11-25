/* ================= Chụp & đọc giấy tờ ================= */
function setFile(k,f,fromCam){
  files[k]=f;if(!fromCam)delete camFix[k];
  if(k==='cccd_back')cccdQR=peekQR;
  paintRvImgs();
  if(!stacking)maybeScan();
}
/* Chỉ cho chụp trực tiếp: mở camera của trình duyệt (getUserMedia), không có nút chọn ảnh từ thư viện.
   Cần https hoặc localhost. Nếu trình duyệt không hỗ trợ thì mới quay về ô chụp của hệ điều hành. */
const CAM_TXT={cccd_back:'CCCD mặt sau (có mã QR)',cccd_front:'CCCD mặt trước',cavet:'Cà vẹt xe'};
const CAM_HINT={cccd_back:'Đặt MẶT SAU thẻ (có mã QR) vừa khít khung, giữ yên máy',cccd_front:'Mã QR chưa đủ thông tin — chụp thêm MẶT TRƯỚC thẻ',cavet:'Đặt Cà vẹt xe vừa khít khung, giữ yên máy'};
let camStream=null,camKey=null;
const IN_APP=/Zalo|FBAN|FBAV|FB_IAB|Messenger|Instagram|Line\/|MicroMessenger/i.test(navigator.userAgent);   // trình duyệt nhúng: bắt video toàn màn hình
const camOK=()=>!IN_APP&&!!(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia&&window.isSecureContext);
function closeCam(){camHold=null;delete $('#cam').dataset.rv;countStop();peekStop();if(camStream){camStream.getTracks().forEach(t=>t.stop());camStream=null;}$('#cam').hidden=true;document.body.style.overflow='';}
function camShow(k){countStop();autoOff=false;lastSig='';okRun=0;camKey=k;peekQR=false;peekAcc={};$('#camTitle').textContent=CAM_TXT[k];$('#camHint').textContent=CAM_HINT[k];peekStop();}
let peekN=0,camT0=0,blackN=0;
function frameBlack(c){try{const t=document.createElement('canvas');t.width=t.height=16;const x=t.getContext('2d');x.drawImage(c,0,0,16,16);const d=x.getImageData(0,0,16,16).data;let m=0;for(let i=0;i<d.length;i+=4)m+=d[i]+d[i+1]+d[i+2];return m/(256*3)<6;}catch(e){return false;}}
async function camRestart(){
  try{if(camStream)camStream.getTracks().forEach(t=>t.stop());}catch(e){}
  try{camStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:2560},height:{ideal:1440}},audio:false});
    const v=$('#camVideo');v.srcObject=camStream;await v.play();camTune();blackN=0;}catch(e){tr('black_frame',{kind:'restart_fail'});}
}
const tr=(ev,o)=>{try{fetch('/api/trace',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({ev,...o}),keepalive:true}).catch(()=>{});}catch(e){}};   // báo số liệu luồng quét về log máy chủ (không gửi giá trị)
async function openCam(k){
  camShow(k);peekN=0;camT0=Date.now();tr('cam_open',{kind:k});
  $('#cam').hidden=false;document.body.style.overflow='hidden';
  try{
    camStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:2560},height:{ideal:1440}},audio:false});
    const v=$('#camVideo');
    v.muted=true;v.defaultMuted=true;v.playsInline=true;v.controls=false;
    ['playsinline','webkit-playsinline','muted','disablepictureinpicture','disableremoteplayback'].forEach(n=>v.setAttribute(n,''));
    v.srcObject=camStream;await v.play();camTune();peekLoop();
  }catch(e){closeCam();toast('Không mở được camera. Hãy cho phép dùng camera cho trang này.');}
}
let torchOn=false,okRun=0,lastSig='',countT=0,autoOff=false;
function countStop(){clearInterval(countT);countT=0;const e=$('#camCount');if(e)e.hidden=true;}
function countStart(){
  let n=3;const e=$('#camCount');e.hidden=false;
  const draw=()=>{e.innerHTML=`<span>Đã đọc ổn định, tự chụp sau <b>${n}</b> giây</span><button type="button" id="camCancel">Huỷ</button>`;$('#camCancel').onclick=()=>{countStop();autoOff=true;};};
  draw();countT=setInterval(()=>{n--;if(n<=0){countStop();okRun=0;snap('auto');}else draw();},1000);
}
async function camTune(){      // lấy nét liên tục + nút đèn flash nếu máy hỗ trợ
  const t=camStream&&camStream.getVideoTracks()[0];if(!t||!t.getCapabilities)return;
  const c=t.getCapabilities(),adv=[];
  if(c.focusMode&&c.focusMode.includes('continuous'))adv.push({focusMode:'continuous'});
  if(adv.length)try{await t.applyConstraints({advanced:adv});}catch(e){}
  torchOn=false;$('#camTorch').hidden=!c.torch;$('#camTorch').style.opacity=1;
}
async function toggleTorch(){
  const t=camStream&&camStream.getVideoTracks()[0];if(!t)return;
  try{await t.applyConstraints({advanced:[{torch:!torchOn}]});torchOn=!torchOn;$('#camTorch').style.opacity=torchOn?1:.5;}catch(e){}
}
function cropFrame(maxW){
  const v=$('#camVideo');if(!v.videoWidth)return null;
  const vr=v.getBoundingClientRect(),g=$('#camFrame').getBoundingClientRect();
  const sc=Math.max(vr.width/v.videoWidth,vr.height/v.videoHeight);
  const ox=(v.videoWidth*sc-vr.width)/2,oy=(v.videoHeight*sc-vr.height)/2,m=0.05;           // chừa viền 5% quanh khung
  let x=(g.left-vr.left+ox)/sc,y=(g.top-vr.top+oy)/sc,w=g.width/sc,h=g.height/sc;
  x-=w*m;y-=h*m;w*=1+2*m;h*=1+2*m;x=Math.max(0,x);y=Math.max(0,y);w=Math.min(w,v.videoWidth-x);h=Math.min(h,v.videoHeight-y);
  const k=maxW&&w>maxW?maxW/w:1,c=document.createElement('canvas');c.width=Math.round(w*k);c.height=Math.round(h*k);
  c.getContext('2d').drawImage(v,x,y,w,h,0,0,c.width,c.height);return c;
}
let snapping=false,stacking=0;
function maybeScan(){if(files.cccd_back&&files.cavet&&!scanning&&!stacking)setTimeout(scanNow,150);}   // đủ 2 giấy tờ + ghép ảnh xong → tự đọc, không cần bấm
