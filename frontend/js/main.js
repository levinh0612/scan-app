/* ================= Khởi động ================= */
checkPrinter();setInterval(()=>{if(!document.hidden)checkPrinter();},10000);
{const dr=loadDraft();if(!dr)initState();renderPhieu();goStep(2,true);}
Jobs.refresh();
setInterval(()=>{if(!document.hidden)Jobs.refresh();},3000);

/* co phiếu vừa bề ngang màn hình (dùng transform, giữ chiều cao đúng) */
function fitPhieu(){const st=document.getElementById('stage'),ph=document.getElementById('phieu');if(!st||!ph)return;
  ph.style.transform='none';const w=ph.offsetWidth,avail=st.clientWidth;if(!w||!avail)return;const k=Math.min(1,avail/w);
  ph.style.transform=k<1?'scale('+k+')':'none';st.style.height=k<1?Math.ceil(ph.offsetHeight*k)+'px':'auto';}
addEventListener('resize',fitPhieu);addEventListener('orientationchange',fitPhieu);
new MutationObserver(fitPhieu).observe(document.getElementById('phieu'),{childList:true,subtree:true});
setTimeout(fitPhieu,0);

$('#prnBox').onclick=()=>$('#btnPrn').click();
$('#tabHd').onclick=hdHome;
$('#hdv').addEventListener('click',e=>{const b=e.target.closest('[data-seg]');if(b)b.dataset.seg==='rp'?hdReport():hdHome();});   // điện thoại: Hợp đồng ⇄ Báo cáo cùng 1 tab
$('#tabRp').onclick=()=>hdReport();
$('#tabSt').onclick=hdSettings;
$('#tabHome').addEventListener('click',()=>{if(!$('#hdv').hidden)hdClose();});
api('/api/settings').then(s=>{DEF=s;if(+s.le_phi_ky>0&&!state.le_phi)state.le_phi={value:String(s.le_phi_ky),status:'ok',note:'Mặc định từ Cài đặt.'};if(+s.so_ngay_ky&&state.so_ngay&&!state.so_ngay.edited)state.so_ngay.value=String(s.so_ngay_ky);}).catch(()=>{});
hdStatsRefresh();

