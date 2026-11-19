export function installPrints(start){
  const prints=document.querySelector('#prints');
  const image=document.querySelector('#studioPrint');
  const buttons=[...prints.querySelectorAll('[data-print]')];
  const select=key=>{
    const button=buttons.find(b=>b.dataset.print===key)||buttons[0];
    const label=button.textContent.trim();
    image.alt='Nexus-Aquila NW-01 机械白头海雕，'+label+'，Blender Cycles 渲染';
    image.src=button.dataset.file;
    prints.querySelector('figcaption').textContent=label;
    for(const b of buttons)b.setAttribute('aria-pressed',String(b===button));
  };
  for(const b of buttons)b.addEventListener('click',()=>select(b.dataset.print));
  document.querySelector('#openPrints').addEventListener('click',()=>{
    const pose=document.querySelector('input[name="pose"]:checked')?.value;
    const view=document.querySelector('#scene').dataset.view;
    select({axial:'axial',back:'rear',side:'left',rightview:'right',top:'overhead',bottom:'ventral'}[view]||pose);
    prints.showModal();
  });
  const [mode,plate]=location.hash.slice(1).split('/');
  if(mode!=='studio'){start();return}
  const loading=document.querySelector('#loading');loading.hidden=true;
  select(plate);
  const observer=new MutationObserver(()=>{
    if(prints.open)return;
    observer.disconnect();
    try{history.replaceState(null,'','#front')}catch{}
    loading.hidden=false;start();
  });
  observer.observe(prints,{attributes:true,attributeFilter:['open']});
  prints.showModal();
}
