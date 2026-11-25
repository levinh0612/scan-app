/* --- Lưu hợp đồng + tải ảnh đã quét --- */
async function uploadShots(id,fs){
  for(const [kind,blob] of Object.entries(fs)){
    if(!blob)continue;
    try{await fetch(`/api/contracts/${id}/anh/${kind}`,{method:'POST',headers:AU.tok?{'X-Session':AU.tok}:{},body:blob});}catch(e){}
  }
}
async function saveContract(snap){
  const fs={cccd:files.cccd_back,cavet:files.cavet};
  try{
    const r=await api('/api/contracts',{method:'POST',body:JSON.stringify(snap)});
    toast(r.duplicate?`Hợp đồng này đã được lưu trước đó (${r.contract.ma}).`:`Đã lưu hợp đồng ${r.contract.ma} — hạn ${r.contract.den_ngay_vn}`);
    if(!r.duplicate)uploadShots(r.contract.id,fs);
    hdStatsRefresh();return r;
  }catch(e){toast('Chưa lưu được hợp đồng vào kho (vẫn in được). Báo kỹ thuật nếu lặp lại.');}
}

/* --- Thống kê + thanh tab --- */
async function hdStatsRefresh(){
  await authInit();
  $('#tabHd').hidden=false;$('#tabRp').hidden=$('#tabSt').hidden=!AU.local;
  hdOK=true;
  if(!AU.authed)return null;
  try{const st=await api('/api/contracts/stats');const n=st.qua_han+st.sap_han;const b=$('#hdBadge');b.hidden=!n;b.textContent=n;$('#hdCnt').textContent=st.dang_cam||'';return st;}
  catch(e){return null;}
}
function hdClose(){$('#hdv').hidden=true;document.body.style.overflow='';setTab('tabHome');if(window.homeHide)homeHide();}

