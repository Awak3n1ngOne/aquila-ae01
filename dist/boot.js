import {installPrints} from './studio-prints.js';

// Show the linked landscape while the renderer and the geometry are still loading.
const linkedPose=location.hash.slice(1).split('/')[0];
const initialOption=Array.from(document.querySelectorAll('input[name="pose"]')).find(option=>option.value===linkedPose);
document.querySelector('#bench').dataset.pose=initialOption?.value??'front';
if(initialOption)initialOption.checked=true;

installPrints(()=>import('./app.js').catch(error=>{
  const status=document.querySelector('#loading');
  if(status.textContent.includes('正在装配'))status.textContent='三维模型暂未载入。可以打开摄影棚查看原图，或重新载入页面。';
  status.hidden=false;
  console.error(error);
}));
