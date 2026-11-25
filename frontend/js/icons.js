/* Bộ icon dạng SF Symbols (SVG nét liền, theo màu chữ). Dùng ic('tên') trong template HTML. */
const IC_PATH={
  camera:'<path d="M4 8.5A2 2 0 016 6.5h2l1.3-2h5.4l1.3 2h2a2 2 0 012 2V17a2 2 0 01-2 2H6a2 2 0 01-2-2z"/><circle cx="12" cy="12.5" r="3.4"/>',
  check:'<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  x:'<path d="M6 6l12 12M18 6L6 18"/>',
  dots:'<circle cx="5.5" cy="12" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/><circle cx="18.5" cy="12" r="1.4" fill="currentColor"/>',
  warn:'<path d="M12 4.2L21 19.5H3z"/><path d="M12 10v4.2M12 16.9v.1"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5.2M12 7.9v.1"/>',
  lock:'<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 018 0v2.5"/>',
  inbox:'<path d="M3.5 13.5l2.4-7.2A2 2 0 017.8 5h8.4a2 2 0 011.9 1.3l2.4 7.2"/><path d="M3.5 13.5V18a2 2 0 002 2h13a2 2 0 002-2v-4.5h-5.2a3 3 0 01-6.6 0z"/>'
};
const ic=n=>`<svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC_PATH[n]}</svg>`;
