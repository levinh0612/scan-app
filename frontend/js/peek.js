/* Xem trước trực tiếp: mỗi lần chỉ 1 yêu cầu, khung nhỏ (1000px), kết quả hiện ngay trên màn hình camera. Không lưu gì. */
const SHARP_OK=90;       // đủ nét khi > 90 (nghiêm: phải LỚN HƠN)
const PEEK_NAMES={ho_ten:'Họ tên',cccd:'Số CCCD',ngay_sinh:'Ngày sinh',dia_chi:'Địa chỉ',ngay_cap:'Ngày cấp',bks:'Biển số',nhan_hieu:'Nhãn hiệu - loại',so_loai:'Loại',so_khung:'Số khung',so_may:'Số máy',mau:'Màu sơn',mau_son:'Màu sơn'};
const PEEK_EXPECT={cavet:['bks','nhan_hieu','so_khung','so_may','mau'],cccd_front:['cccd','ho_ten'],cccd_back:['cccd','ho_ten','dia_chi','ngay_cap']};
let peekTimer=0,peekBusy=false,peekQR=false,cccdQR=false,peekAcc={},liveAcc={};   // peekAcc: gom kết quả nhiều khung hình của lần ngắm hiện tại; liveAcc: giữ lại để điền vào phiếu   // peekQR: khung hiện tại đã đọc đủ từ mã QR
function peekStop(){clearTimeout(peekTimer);peekTimer=0;delete $('#camFrame').dataset.s;$('#camLive').hidden=true;$('#camLive').innerHTML='';}
function peekLoop(){
  clearTimeout(peekTimer);
  peekTimer=setTimeout(async()=>{
    if($('#cam').hidden||camHold)return;
    const c=!peekBusy&&cropFrame(1400);
    if(c&&frameBlack(c)){      // khung đen (iOS đôi khi trả canvas đen khi camera bị treo): không gửi lên máy chủ, khởi động lại camera
      blackN++;if(blackN===3){tr('black_frame',{kind:camKey,sec:Math.round((Date.now()-camT0)/1000)});camRestart();}
      $('#camLive').hidden=false;$('#camLive').innerHTML='<div class="q bad">Camera chưa có hình — đang khởi động lại…</div>';
    }else if(c){blackN=0;
      peekBusy=true;const k=camKey;
      try{
        const b=await new Promise(r=>c.toBlob(r,'image/jpeg',.8));
        const fd=new FormData();fd.append('kind',k);fd.append('image',b,'p.jpg');
        const r=await fetch('/api/peek',{method:'POST',body:fd});
        if(r.ok&&!$('#cam').hidden&&!camHold&&k===camKey)peekShow(await r.json());
      }catch(e){}
      peekBusy=false;
    }
    if(!$('#cam').hidden&&!camHold)peekLoop();
  },700);
}
function peekMerged(){      // ô đã gom từ các khung hình; hãng + loại gộp thành 1 dòng
  const f={};for(const[k,v]of Object.entries(peekAcc))f[k]={value:v.value,status:v.status};
  if(f.nhan_hieu||f.so_loai){const a=f.nhan_hieu,b=f.so_loai;delete f.so_loai;
    f.nhan_hieu={value:[a&&a.value,b&&b.value].filter(Boolean).join(' - '),status:(a&&a.status==='ok'&&(!b||b.status==='ok'))?'ok':'check'};}
  return f;
}
let peekSeq=0;
function peekShow(d){peekSeq++;peekN++;peekQR=camKey==='cccd_back'&&!!(d.qr&&d.fields&&d.fields.cccd&&d.fields.ho_ten&&d.fields.dia_chi);
  
  for(const[k,v]of Object.entries(d.fields||{})){        // gom: ô nào đã đọc được thì giữ lại, khung sau đọc hỏng cũng không mất
    if(!v.value)continue;       // bỏ phiếu theo khung hình, ưu tiên khung GẦN ĐÂY và khung NÉT: tay run → khung mờ gần như không có tiếng nói; giữ yên → khung nét đẩy giá trị sai cũ ra
    const p=peekAcc[k]||(peekAcc[k]={votes:{},value:'',status:'check',n:0});
    const w=d.sharp>SHARP_OK?1:(d.sharp>=SHARP_OK*0.6?0.3:0);
    if(!p.fresh||p.fresh!==peekSeq){for(const x of Object.values(p.votes))x.n*=0.7;p.fresh=peekSeq;}     // mỗi khung hình: phiếu cũ giảm 30%
    const e=p.votes[v.value]||(p.votes[v.value]={n:0,ok:false});e.n+=w;e.ok=e.ok||(v.status==='ok'&&w>0);
    let best=v.value,bs=-1;for(const[val,x]of Object.entries(p.votes)){const sc=x.n+(x.ok?.8:0)+(val===v.value&&w>0?.1:0);if(sc>bs){bs=sc;best=val;}}
    p.value=best;p.status=p.votes[best].ok?'ok':'check';p.n=p.votes[best].n;
    liveAcc[k]={value:peekAcc[k].value,status:peekAcc[k].status};
  }
  const f=peekMerged();
  const keys=[...(PEEK_EXPECT[camKey]||[])];Object.keys(f).forEach(k=>{if(!keys.includes(k))keys.push(k);});
  const rows=keys.map(k=>{const v=f[k];
    const nodau=k==='ho_ten'&&v&&v.value&&!/[^\x00-\x7f]/.test(v.value);     // OCR không ra dấu: đủ dấu chỉ có trong mã QR
    return v&&v.value?`<div class="r ${v.status==='ok'&&!nodau?'ok':'chk'}"><span>${PEEK_NAMES[k]||k}</span><b>${k==='dia_chi'?addrH(v.value):esc(v.value)}${nodau?'<small>chưa có dấu — sẽ đủ dấu khi quét mã QR ở mặt sau</small>':''}</b></div>`:`<div class="r bad"><span>${PEEK_NAMES[k]||k}</span><b>Chưa đọc được</b></div>`;}).join('');
  const exp=PEEK_EXPECT[camKey]||[],miss=exp.filter(k=>!(f[k]&&f[k].value)).map(k=>PEEK_NAMES[k]||k);
  const GLARE=(d.glare||0)>0.03;const SOK=d.sharp>SHARP_OK&&!GLARE;$('#camFrame').dataset.s=SOK?'ok':'bad';       // khung xanh = đủ nét, đỏ = chưa nét
  const chk=Object.values(f).some(v=>v.status!=='ok');
  const sharp=GLARE?`<div class="q bad">Bị loá sáng — nghiêng máy một chút để tránh bóng đèn</div>`:!SOK?`<div class="q bad">Chưa đủ nét (${d.sharp}/${SHARP_OK}) — giữ yên máy, lùi ra một chút, đủ sáng</div>`:(miss.length?`<div class="q no">Ảnh nét. Đã đọc ${exp.length-miss.length}/${exp.length} ô — còn thiếu: ${miss.join(', ')}. Cứ giữ máy, ô đã đọc được sẽ được nhớ lại.</div>`:`<div class="q ok">Ảnh nét, đã đọc đủ — ${chk?'xem lại các ô vàng rồi ':''}bấm chụp</div>`);
  $('#camLive').innerHTML=sharp+rows;
  const KEYF={cavet:['bks','so_khung','so_may'],cccd_front:['cccd','ho_ten'],cccd_back:['cccd','ho_ten','dia_chi']}[camKey]||[];
  const cur=d.fields||{},sig=KEYF.map(k=>cur[k]&&cur[k].value||'').join('|');   // giá trị đọc ở CHÍNH khung hình này
  const ready=SOK&&!miss.length&&KEYF.every(k=>cur[k]&&cur[k].value)&&(camKey!=='cccd_back'||peekQR);
  if(!ready||sig!==lastSig){okRun=ready?1:0;lastSig=ready?sig:'';if(countT)countStop();}   // đổi giá trị / mất nét → làm lại từ đầu
  else okRun++;
  if(okRun>=3&&!countT&&!autoOff)countStart();
  $('#camLive').hidden=false;
}
$('#camVideo').addEventListener('webkitbeginfullscreen',function(){try{this.webkitExitFullscreen();}catch(e){}});
