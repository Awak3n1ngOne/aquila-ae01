import * as T from './assets/three.module.js';
import {OrbitControls} from './assets/OrbitControls.js';
import {loadEagle,sheet,poseNames,studioDistance,landing,environmentIntensity} from './solid-rig.js';

const $=selector=>document.querySelector(selector);
const host=$('#viewport'),canvas=$('#scene'),slider=$('#position'),inspector=$('#inspection');
const assemblies=[
  ['OPTICS','头颈与光学','白色羽甲的中脊向羽尖收窄，两侧刻槽顺着羽缘分叉。眉甲下方是琥珀色光学眼和活动眼睑。'],
  ['BREAST ARMOR','胸甲','层叠的护甲沿胸腔的弧面安装，覆盖在左右翼根之间。'],
  ['PORT WING','左翼飞羽','独立的主飞羽和覆羽由肩、肘、腕三段翼架支撑。'],
  ['STARBOARD WING','右翼飞羽','长飞羽在翼尖分叉。着陆减速时，翼腕转动，飞羽迎向来流。'],
  ['SHOULDER DRIVE','翼根传动','肩轴齿轮、铰接连杆和伸缩活塞共同带动翼架。'],
  ['TAIL FAN','尾扇','白色尾羽逐片安装在尾部铰座上。'],
  ['TALONS','双爪','金色趾节与深色弯爪在踝轴下方合拢。'],
  ['THORACIC FRAME','胸内骨架','内环和贯穿胸腔的主轴支撑外部装甲。']
];
const poseNotes={
  side:{3:'侧向滑翔时，长飞羽沿翼腕向外扇开。旋转可看到前后两翼的高度差。',6:'飞行时双腿收在腹部，金色趾节折起，深色爪尖向内弯曲。'},
  perched:{4:'收翼时，活塞贴近肩部。展开双翼可以观察肩轴和翼腕铰链的朝向。',6:'每只脚的四趾分前后包住横杠。展开双翼和转头时，脚爪仍停在栖架上。'},
  rear:{4:'从背面可以同时看到左右翼梁、肩轴和成对的伸缩活塞。',5:'白色尾羽从脊背下方向外扇开，层叠处可以看到独立的羽片。'}
};
const reduce=matchMedia('(prefers-reduced-motion:reduce)');
const state={position:0,playing:false,selected:4,
  spread:1,spreadGoal:1,yaw:0,yawGoal:0,blink:0,blinkAt:null,flap:0,demoAt:null,clock:0};
const clamp=T.MathUtils.clamp,smooth=T.MathUtils.smoothstep;
const phaseLabel=$('#flightPhase');
const phases=[[0,'第一次振翅'],[landing.beat,'第二次振翅'],[landing.descent,'近地收翅'],
  [landing.touchdown,'触地缓冲'],[landing.compression,'双翼归位'],[landing.settled,'站稳']];
for(const seconds of [...phases.map(([at])=>at),landing.seconds]){
  const mark=document.createElement('i');
  mark.style.left=100*seconds/landing.seconds+'%';
  $('.stops').append(mark);
}
let renderer;
try {
  renderer=new T.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:'high-performance'});
} catch {
  $('#loading').textContent='这个三维展品需要 WebGL 2。请在开启硬件加速的浏览器中打开。';
  throw new Error('WebGL 2 unavailable');
}
renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.6));
renderer.setClearColor(0x000000,0);
renderer.outputColorSpace=T.SRGBColorSpace;
renderer.toneMapping=T.AgXToneMapping??T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.0;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.shadowMap.autoUpdate=false;
const scene=new T.Scene(),camera=new T.PerspectiveCamera(29,1,.08,85);
const shotCamera=camera.clone();
const tuckOffset=new T.Vector3();
const controls=new OrbitControls(camera,canvas);
controls.enableDamping=true;controls.dampingFactor=.12;controls.rotateSpeed=.62;
controls.minDistance=3.2;controls.maxDistance=33;controls.minZoom=.55;controls.maxZoom=6;controls.enablePan=false;
const radianceReady=new T.TextureLoader().loadAsync(document.querySelector('meta[name="aquila-studio"]').content).then(texture=>{
  texture.mapping=T.EquirectangularReflectionMapping;
  texture.colorSpace=T.SRGBColorSpace;
  const pmrem=new T.PMREMGenerator(renderer);
  scene.environment=pmrem.fromEquirectangular(texture).texture;
  scene.environmentIntensity=environmentIntensity;
  texture.dispose();pmrem.dispose();
}).catch(()=>{scene.add(new T.HemisphereLight(0xffefda,0xaf9178,.9))});
scene.add(new T.HemisphereLight(0xfff4e6,0x8d725c,.23));
function light(p,color,power){
  const l=new T.DirectionalLight(color,power);l.position.set(...p);scene.add(l,l.target);return l;
}
const key=light([-4.2,7,6],0xffecda,2.12);
key.castShadow=true;key.shadow.mapSize.set(2048,2048);
Object.assign(key.shadow.camera,{left:-7.4,right:7.4,top:6.3,bottom:-6.3,near:.2,far:25});
key.shadow.normalBias=.009;key.shadow.bias=-.00017;key.shadow.radius=3;
light([5.3,4,-5],0xe6efff,1.46);light([5,2.2,4],0xffe9d0,.33);
const floor=new T.Mesh(new T.PlaneGeometry(65,65),new T.ShadowMaterial({color:0x735c48,opacity:.062,depthWrite:false}));
floor.rotation.x=-Math.PI/2;floor.receiveShadow=true;scene.add(floor);
const contactCanvas=document.createElement('canvas');contactCanvas.width=contactCanvas.height=96;
const ctx=contactCanvas.getContext('2d'),grad=ctx.createRadialGradient(48,48,0,48,48,48);
grad.addColorStop(0,'rgba(88,60,41,.24)');grad.addColorStop(.5,'rgba(108,81,58,.10)');grad.addColorStop(1,'rgba(116,88,67,0)');
ctx.fillStyle=grad;ctx.fillRect(0,0,96,96);
const contactMap=new T.CanvasTexture(contactCanvas);contactMap.colorSpace=T.SRGBColorSpace;
const contact=new T.Mesh(new T.PlaneGeometry(1,1),new T.MeshBasicMaterial({map:contactMap,transparent:true,depthWrite:false,toneMapped:false}));
contact.rotation.x=-Math.PI/2;scene.add(contact);
const footShadows=[-1,1].map(()=>{
  const patch=new T.Mesh(contact.geometry,contact.material.clone());
  patch.rotation.x=-Math.PI/2;patch.scale.set(1.25,.9,1);scene.add(patch);return patch;
});
// A fixed floor datum gives the approaching feet a visible place to land.
const padLines=[];
for(let i=0;i<96;i++){
  const a=i*Math.PI/48,b=(i+1)*Math.PI/48;
  if(i%24===0)padLines.push(1.99*Math.cos(a),0,1.99*Math.sin(a),2.25*Math.cos(a),0,2.25*Math.sin(a));
  if(i%24>1&&i%24<22)padLines.push(2.12*Math.cos(a),0,2.12*Math.sin(a),2.12*Math.cos(b),0,2.12*Math.sin(b));
}
const padGeometry=new T.BufferGeometry();
padGeometry.setAttribute('position',new T.Float32BufferAttribute(padLines,3));
const landingPad=new T.LineSegments(padGeometry,new T.LineBasicMaterial({color:0x866b50,transparent:true,depthWrite:false}));
landingPad.position.set(0,landing.ground+.003,.24);scene.add(landingPad);
$('#ground').style.display='none';
const cameras=new Set(['axial','side','rightview','back','top','bottom']);
function readAddress(){
  const [pose,view]=location.hash.slice(1).split('/');
  return {pose:Object.hasOwn(poseNames,pose)?pose:'front',view:cameras.has(view)?view:'hero'};
}
function saveAddress(view='hero'){
  const address='#'+activePose+(cameras.has(view)?'/'+view:'');
  if(location.hash!==address)try{history.replaceState(null,'',address)}catch{}
}
const initialAddress=readAddress();
let activePose=initialAddress.pose,transition=1;
let model;
try{[model]=await Promise.all([loadEagle(),radianceReady])}catch(error){
  $('#loading').textContent='三维模型载入失败，请重新加载页面。';
  console.error('Unable to load the Aquila solid assembly',error);throw error;
}
model.setPreset(activePose);scene.add(model.root);
const anchor=new T.Vector3(),ray=new T.Raycaster();
const ndc=new T.Vector2(), guidePath=$('#leader'), pin=$('#pin'), caption=$('#caption');
const frameSize={w:0,h:0,scale:1,vertical:8,usableW:.8,usableH:.82};
let viewGoal=null,activeView='hero',raf=0,visible=true,prevTime=0,lastShadow=-Infinity;
const eyeDirection=new T.Vector3(),currentOrbit=new T.Spherical(),targetOrbit=new T.Spherical();
let lastPose='',lastReadout='',lastGuide='',flightTick=null,ready=false;
function invalidate(){
  if(ready&&!document.hidden&&visible&&!raf)raf=requestAnimationFrame(draw);
}
function setStatus(message){
  const status=$('#loading');status.hidden=!message;if(message)status.textContent=message;
}
function layoutStudio(){
  $('#bench').dataset.pose=activePose;
  $('.transport').hidden=activePose!=='front';
  canvas.setAttribute('aria-label','机械白头海雕 · '+poseNames[activePose]+'。拖动绕同一模型旋转，方向键调整视角，加减号缩放，Home 复位。');
  for(const input of document.querySelectorAll('input[name="pose"]'))input.checked=input.value===activePose;
  $('#partCount').textContent=model.count.toLocaleString('zh-CN')+' 个机械零件 · 8 个总成';
}
function switchPose(key){
  if(!Object.hasOwn(poseNames,key)||key===activePose)return;
  const blend=!reduce.matches&&key!=='front'&&activePose!=='front';
  halt();model.setPreset(key,blend);transition=blend?0:1;
  activePose=key;layoutStudio();resize();reset(!blend);
  if(key==='front'&&!reduce.matches)playFlight();
  saveAddress();
  invalidate();
}
function fitHeight(f){
  return Math.max(f.width/((frameSize.w/frameSize.h||1)*frameSize.usableW),f.height/frameSize.usableH);
}
function view(id,instant=false){
  activeView=id;canvas.dataset.view='moving';saveAddress(id);
  const f=model.fit(id==='side'?'sideview':id==='detail'?'hero':id);
  const t=id==='detail'?model.focus(state.selected,new T.Vector3()):new T.Vector3().fromArray(f.center);
  if(id==='detail'&&activePose==='front')t.sub(model.flightOrigin);
  const dir=new T.Vector3().fromArray(f.eye);
  let zoom=frameSize.vertical/fitHeight(f);
  if(id==='detail'){
    zoom=state.selected===0?Math.min(controls.maxZoom,frameSize.vertical/fitHeight({width:2.64,height:1.76})):2.5;
  }
  viewGoal={pos:t.clone().addScaledVector(dir,studioDistance),target:t,zoom};
  for(const b of document.querySelectorAll('.orbit-picker [data-view]'))b.setAttribute('aria-pressed',String(b.dataset.view===id));
  if(instant||reduce.matches){
    controls.target.copy(t);camera.position.copy(viewGoal.pos);camera.zoom=viewGoal.zoom||1;
    camera.updateProjectionMatrix();controls.update();viewGoal=null;canvas.dataset.view=id;
  }
  invalidate();
}
function changePart(id){
  state.selected=id;caption.textContent=assemblies[id][0];
  document.querySelectorAll('[data-part]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.part)===id)));
  $('#selectionText').textContent=(poseNotes[activePose]?.[id]??assemblies[id][2])+'（'+model.counts[id]+' 件）';
  if(activeView==='detail')view('detail');
  lastGuide='';invalidate();
}
function stopDemo(){
  if(state.demoAt!==null){state.spreadGoal=state.spread;state.yawGoal=state.yaw}
  state.demoAt=null;state.flap=0;state.blink=0;state.blinkAt=null;
}
function halt(){
  state.playing=false;flightTick=null;stopDemo();syncButtons();invalidate();
}
function playFlight(){
  if(activePose!=='front'||state.playing)return;
  stopDemo();
  if(state.position>=1)state.position=0;
  state.spread=state.spreadGoal=1;state.yaw=state.yawGoal=0;
  if(activeView==='detail')view('hero',true);
  state.playing=true;flightTick=null;
  syncButtons();invalidate();
}
function seek(value){
  halt();state.position=clamp(value,0,1);
  if(activePose==='front')state.spread=state.spreadGoal=1;
  syncButtons();invalidate();
}
function reset(instant=true){
  // Flush residual orbit damping so a reset lands in the calibrated camera.
  controls.enableDamping=false;controls.update();controls.enableDamping=true;
  halt();Object.assign(state,{position:reduce.matches?1:0,spread:1,spreadGoal:1,yaw:0,yawGoal:0});
  model.xray(false);$('#xray').setAttribute('aria-pressed','false');
  activeView='hero';changePart(4);view('hero',instant);lastPose='';lastReadout='';syncButtons();invalidate();
}
function syncButtons(){
  $('#bench').toggleAttribute('data-flying',state.playing);
  $('#play').setAttribute('aria-pressed',String(state.playing));
  $('#pause').setAttribute('aria-pressed',String(!state.playing&&state.position>0&&state.position<1));
  $('#motion').setAttribute('aria-pressed',String(state.demoAt!==null));
  $('#motion').textContent=state.demoAt===null?'动作演示':'暂停演示';
}
function inspect(id){halt();changePart(id)}
for(const [id,[name,zh]] of assemblies.entries()){
  const b=document.createElement('button');b.type='button';b.textContent=zh;b.dataset.part=id;b.title=name;
  $('.all-parts').append(b);
}
document.querySelectorAll('[data-part]').forEach(b=>b.onclick=()=>inspect(Number(b.dataset.part)));
$('#play').onclick=playFlight;$('#pause').onclick=halt;$('#stop').onclick=()=>{transition=1;reset();seek(0)};
slider.oninput=()=>seek(+slider.value/1000);
$('#driveToggle').onclick=()=>{
  const open=$('#driveControls').hidden;$('#driveControls').hidden=!open;
  $('#driveToggle').setAttribute('aria-expanded',String(open));
  $('#driveToggle').title=open?'收起动作控制':'展开动作控制';
};
function wingsAreFolded(){
  if(activePose==='perched')return state.spreadGoal>.5;
  if(activePose!=='front')return state.spreadGoal<.5;
  if(state.spreadGoal===1)return state.position*landing.seconds>=landing.compression;
  return state.spreadGoal<1;
}
$('#spread').onclick=()=>{
  halt();
  if(activePose==='front')state.spreadGoal=wingsAreFolded()?2:0;
  else state.spreadGoal=state.spreadGoal>.5?0:1;
  syncButtons();invalidate();
};
$('#turn').onclick=()=>{halt();state.yawGoal=state.yawGoal>.12?-.36:.78;syncButtons();invalidate()};
$('#blink').onclick=()=>{halt();state.blinkAt=state.clock;syncButtons();invalidate()};
$('#motion').onclick=()=>{
  if(state.demoAt===null){halt();state.demoAt=state.clock}else stopDemo();
  syncButtons();invalidate();
};
$('#help').onclick=$('#inspectMore').onclick=()=>{halt();inspector.showModal()};
$('#openPrints').addEventListener('click',halt);
$('#close').onclick=()=>inspector.close();
$('#exportGLB').onclick=async()=>{
  const button=$('#exportGLB');button.disabled=true;
  try{
    const blob=await model.download(),url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download='Nexus-Aquila-NW-01.glb';document.body.append(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),30000);
  }finally{button.disabled=false}
};
inspector.addEventListener('click',e=>{if(e.target===inspector){
  const r=inspector.getBoundingClientRect();
  if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)inspector.close();
}});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{view(b.dataset.view);if(inspector.open)inspector.close()});
$('#xray').onclick=()=>{model.xray(!model.cutaway);renderer.shadowMap.needsUpdate=true;$('#xray').setAttribute('aria-pressed',String(model.cutaway));inspector.close();invalidate()};
document.querySelectorAll('input[name="pose"]').forEach(input=>input.onchange=()=>{if(input.checked)switchPose(input.value)});
window.addEventListener('hashchange',()=>{const address=readAddress();switchPose(address.pose);view(address.view)});
document.addEventListener('keydown',e=>{
  if(inspector.open||$('#prints').open||e.repeat||e.altKey||e.ctrlKey||e.metaKey)return;
  if(e.code==='Space'&&(activePose==='front'||state.demoAt!==null)&&!e.target.closest?.('button,input,a')){
    e.preventDefault();if(state.playing||state.demoAt!==null)halt();else playFlight();
  }
});
canvas.addEventListener('keydown',e=>{
  if(e.key==='Home'){e.preventDefault();reset();return}
  if(['+','=','-'].includes(e.key)){
    e.preventDefault();camera.zoom=clamp(camera.zoom*(e.key==='-'?.87:1.15),.55,6);camera.updateProjectionMatrix();invalidate();return;
  }
  if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;
  e.preventDefault();viewGoal=null;
  const orbit=new T.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
  if(e.key==='ArrowLeft')orbit.theta-=.12;if(e.key==='ArrowRight')orbit.theta+=.12;
  if(e.key==='ArrowUp')orbit.phi-=.10;if(e.key==='ArrowDown')orbit.phi+=.10;
  orbit.makeSafe();camera.position.copy(controls.target).add(new T.Vector3().setFromSpherical(orbit));
  controls.update();invalidate();
});
let pointerStart=null;
canvas.addEventListener('pointerdown',e=>{pointerStart=[e.clientX,e.clientY]});
canvas.addEventListener('pointercancel',()=>{pointerStart=null});
canvas.addEventListener('pointerup',e=>{
  if(!pointerStart)return;
  const distance=Math.hypot(e.clientX-pointerStart[0],e.clientY-pointerStart[1]);pointerStart=null;
  if(distance>5)return;
  const rect=canvas.getBoundingClientRect();ndc.set((e.clientX-rect.left)/rect.width*2-1,1-(e.clientY-rect.top)/rect.height*2);
  ray.setFromCamera(ndc,shotCamera);
  const hit=ray.intersectObjects(model.pickables,false)[0];if(!hit)return;
  inspect(hit.object.userData.assembly);
});
controls.addEventListener('start',()=>{viewGoal=null;activeView='orbit';canvas.dataset.view='orbit';saveAddress();document.querySelectorAll('.orbit-picker button').forEach(b=>b.setAttribute('aria-pressed','false'))});
controls.addEventListener('change',invalidate);


const angles={wing:0,yaw:0};
function readout(){
  const pos=Math.round(state.position*1000);
  model.driveReadout(angles);
  const degree=Math.round(angles.wing),yaw=Math.round(angles.yaw);
  const folded=wingsAreFolded();
  const key=[pos,degree,yaw,Math.round(state.blink*4),Math.round(state.flap*18),folded].join('/');
  if(key===lastReadout)return;lastReadout=key;
  slider.value=pos;
  const seconds=state.position*landing.seconds;
  let phase=phases[0][1];
  for(const [at,label] of phases){
    if(Math.round(seconds*1000)<Math.round(at*1000))break;
    phase=label;
  }
  if(phaseLabel.textContent!==phase)phaseLabel.textContent=phase;
  slider.setAttribute('aria-valuetext',phase+'，'+seconds.toFixed(1)+' / '+landing.seconds+' 秒');
  $('.scrubber').style.setProperty('--fill',pos/10+'%');
  $('#spread').textContent=folded?'展翅':'收翼';
  $('#poseReadout').textContent='翼轴 '+degree+'° · 头颈 '+yaw+'°'+(state.blink>.4?' · 闭眼':'');
  const travel=.65+.35*clamp((degree+45)/90,0,1);
  const curve=$('#strokeCurve');
  curve.setAttribute('d','M9 74 C25 77 29 39 40 39 S55 66 65 66 S78 31 89 31 S103 59 114 59 S129 14 139 14 Q146 14 154 36');
  curve.setAttribute('transform',`translate(0 ${74*(1-travel)-state.flap*5}) scale(1 ${travel})`);
}
function leader(){
  const {w,h,scale:s}=frameSize;
  model.focus(state.selected,anchor);anchor.project(shotCamera);
  const x=(anchor.x+1)*w/2,y=(1-anchor.y)*h/2;
  const mobile=matchMedia('(max-width:700px) and (orientation:portrait)').matches;
  const font=mobile?11:Math.max(10,18*s), length=state.selected===4?164:assemblies[state.selected][0].length*10+8;
  const legendW=mobile?caption.textContent.length*6.7:length*s;
  const leftOfHead=mobile&&activePose==='perched'&&state.selected===4;
  const capX=clamp(leftOfHead?x-legendW-24:x-14*s,mobile?8:Math.min(w*.19,200*s),w-legendW-(mobile?8:w*.13));
  const base=clamp(y-(mobile?Math.max(42,192*s):192*s),font*2,h-font*2);
  const key=[x.toFixed(1),y.toFixed(1),capX.toFixed(1),base.toFixed(1),caption.textContent].join('/');
  if(key===lastGuide)return;lastGuide=key;
  $('#annotation').style.visibility=anchor.z< -1||anchor.z>1||x<0||x>w||y<0||y>h?'hidden':'visible';
  guidePath.setAttribute('d',`M${capX+29*s} ${base}H${capX+legendW} M${capX+29*s} ${base}L${x-15*s} ${y-57*s}L${x} ${y}`);
  guidePath.style.strokeWidth=Math.max(1.1,2*s);
  pin.setAttribute('cx',x);pin.setAttribute('cy',y);pin.setAttribute('r',Math.max(2.7,5.7*s));pin.style.strokeWidth=Math.max(1.8,4*s);
  caption.setAttribute('x',capX);caption.setAttribute('y',base-10*s);caption.style.fontSize=font+'px';
}
function toward(now,target,rate,dt){
  if(reduce.matches)return target;
  const next=T.MathUtils.damp(now,target,rate,dt);
  return Math.abs(next-target)<.0006?target:next;
}
function frameFlightCamera(){
  // Keep orbit and zoom in subject space. The tracking camera renders the real world-space path.
  shotCamera.quaternion.copy(camera.quaternion);
  shotCamera.position.copy(camera.position);
  shotCamera.projectionMatrix.copy(camera.projectionMatrix);
  shotCamera.projectionMatrixInverse.copy(camera.projectionMatrixInverse);
  if(activePose==='front'){
    shotCamera.position.addScaledVector(model.flightOrigin,activeView==='detail'?1:.60);
    if(activeView==='hero'||activeView==='orbit'){
      tuckOffset.set(-.38,-.88,-1.7).applyQuaternion(camera.quaternion);
      shotCamera.position.addScaledVector(tuckOffset,smooth(state.position*landing.seconds,landing.descent+.32,landing.settled));
    }
  }
  shotCamera.updateMatrixWorld(true);
}
function draw(now){
  raf=0;if(document.hidden||!visible)return;
  const elapsed=Math.max(0,(now-prevTime)/1000);
  prevTime=Math.max(now,prevTime);
  const dt=Math.min(elapsed,.1);state.clock+=dt;
  if(state.playing&&flightTick!==null){
    state.position=Math.min(1,state.position+Math.max(0,now-flightTick)/(1000*landing.seconds));
    if(state.position===1){state.playing=false;flightTick=null;syncButtons()}
  }
  if(state.demoAt!==null){
    const phase=state.clock-state.demoAt;
    state.spreadGoal=(.5+.5*Math.cos(phase*1.32))*(activePose==='front'?2:1);
    state.yawGoal=.18+.55*Math.sin(phase*1.12);
    state.flap=reduce.matches?0:.65*Math.sin(phase*3.1);
    const cycle=(phase%3.54)-.81;state.blink=cycle>=0&&cycle<.38?Math.sin(Math.PI*cycle/.38)**1.5:0;
  }else if(state.blinkAt!==null){
    const t=(state.clock-state.blinkAt)/.42;
    if(t>=1){state.blinkAt=null;state.blink=0}else state.blink=Math.sin(Math.PI*t)**1.4;
  }
  state.spread=toward(state.spread,state.spreadGoal,5.5,dt);
  state.yaw=toward(state.yaw,state.yawGoal,5.5,dt);
  const front=activePose==='front';
  const t=state.position,spread=state.spread;
  transition=Math.min(1,transition+dt/1.05);
  if(transition===1&&host.dataset.settled!==activePose)host.dataset.settled=activePose;
  const poseKey=[activePose,t,spread,state.yaw,state.blink,state.flap,transition].join('/');
  if(poseKey!==lastPose){
    lastPose=poseKey;
    const fitOpen=activePose==='perched'&&frameSize.w<frameSize.h?1-.51*(1-spread):1;
    model.root.scale.setScalar(fitOpen);
    model.pose({flightTime:front?t*landing.seconds:null,spread,headTurn:state.yaw,blink:state.blink,flap:state.flap,transition});
    floor.position.y=front?landing.ground:model.ground*fitOpen-(activePose==='perched'?.006:.32);
    const contactTime=landing.touchdown/landing.seconds;
    const approach=smooth(t,landing.descent/landing.seconds,contactTime);
    const altitude=front?1-approach:0;
    landingPad.visible=front;landingPad.material.opacity=.30;
    contact.position.set(front?model.flightOrigin.x:0,floor.position.y+.008,front?model.flightOrigin.z:activePose==='perched'?.24:-.12);
    contact.scale.set(activePose==='perched'?3.85:6.1+3.5*altitude,activePose==='perched'?2.7:3.3+2*altitude,1);
    contact.material.opacity=1-.6*altitude;
    for(let i=0;i<footShadows.length;i++){
      const patch=footShadows[i];
      patch.visible=front;
      if(!patch.visible)continue;
      model.feet[i].getWorldPosition(patch.position);
      patch.position.y=floor.position.y+.012;patch.position.z+=.12;
      patch.material.opacity=1.25*approach;
    }
    if(transition===1&&!state.playing&&state.demoAt===null)renderer.shadowMap.needsUpdate=true;
    if(now-lastShadow>90){renderer.shadowMap.needsUpdate=true;lastShadow=now}
  }
  if(viewGoal){
    const f=1-Math.exp(-10*dt);
    currentOrbit.setFromVector3(eyeDirection.copy(camera.position).sub(controls.target));
    targetOrbit.setFromVector3(eyeDirection.copy(viewGoal.pos).sub(viewGoal.target));
    const angle=targetOrbit.theta-currentOrbit.theta;
    currentOrbit.theta+=Math.atan2(Math.sin(angle),Math.cos(angle))*f;
    currentOrbit.phi=T.MathUtils.lerp(currentOrbit.phi,targetOrbit.phi,f);
    currentOrbit.radius=T.MathUtils.lerp(currentOrbit.radius,targetOrbit.radius,f);
    controls.target.lerp(viewGoal.target,f);
    camera.position.copy(controls.target).add(eyeDirection.setFromSpherical(currentOrbit));
    camera.zoom=T.MathUtils.lerp(camera.zoom,viewGoal.zoom,f);
    if(camera.position.distanceTo(viewGoal.pos)<.008&&Math.abs(camera.zoom-viewGoal.zoom)<.002){
      camera.position.copy(viewGoal.pos);controls.target.copy(viewGoal.target);camera.zoom=viewGoal.zoom;viewGoal=null;canvas.dataset.view=activeView;
    }
    camera.updateProjectionMatrix();
  }
  const changing=controls.update(dt);
  frameFlightCamera();renderer.render(scene,shotCamera);leader();readout();
  if(state.playing)flightTick=flightTick===null?performance.now():Math.max(flightTick,now);
  if(transition<1||state.playing||state.demoAt!==null||state.blinkAt!==null||state.spread!==state.spreadGoal||
     state.yaw!==state.yawGoal||viewGoal||changing)invalidate();
}
function resize(){
  const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;
  const narrow=matchMedia('(max-width:700px) and (orientation:portrait)').matches;
  Object.assign(frameSize,{w,h,usableW:narrow?.96:.79,usableH:narrow?.92:.84,scale:Math.min(w/sheet.width,h/sheet.height)});
  frameSize.vertical=fitHeight(model.fit());
  const v=frameSize.vertical;
  renderer.setSize(w,h,false);camera.aspect=w/h;
  camera.fov=T.MathUtils.radToDeg(2*Math.atan(v/(2*studioDistance)));camera.updateProjectionMatrix();
  lastGuide='';invalidate();
}
new ResizeObserver(resize).observe(host);
if('IntersectionObserver' in window)new IntersectionObserver(([entry])=>{
  visible=entry.isIntersecting;flightTick=null;if(visible){prevTime=performance.now();invalidate()}
}).observe(host);
document.addEventListener('visibilitychange',()=>{flightTick=null;prevTime=performance.now();invalidate()});
reduce.addEventListener('change',()=>{if(reduce.matches&&activePose==='front')seek(1);invalidate()});
layoutStudio();changePart(4);resize();view(initialAddress.view,true);
if(activePose==='front'&&!reduce.matches)playFlight();else state.position=1;
syncButtons();
setStatus('');ready=true;invalidate();
