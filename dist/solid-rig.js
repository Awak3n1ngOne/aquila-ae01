import * as T from './assets/three.module.js';
import {GLTFLoader} from './assets/addons/loaders/GLTFLoader.js';
import {rig} from './assets/aquila-rig.js';

export const poseNames={front:'正面着陆',side:'侧向滑翔',perched:'收翼站立',rear:'背面展翅'};
export const studioDistance=rig.distance;
export const environmentIntensity=rig.environmentIntensity??10.24;
export const sheet={width:1672,height:941};
export const landing=rig.landing;
const markSpecs=[
  ['head',[.407,.53,.51]],['body',[0,-.02,.54]],['wing.L',[-.94,.14,-.19]],
  ['wing.R',[1.10,.14,-.15]],['wing.R',[.06,.03,.16]],['tail',[.31,-.16,-.62]],
  ['foot.R',[.01,-.31,.11]],['core',[.03,.08,-.05]]
];
const smooth=T.MathUtils.smoothstep;
const wv=(x,y,z)=>new T.Vector3(x,z,-y);
const axisY=new T.Vector3(0,1,0),axisZ=new T.Vector3(0,0,1);
async function inflate(bytes){
  if(bytes[0]!==31||bytes[1]!==139)return bytes;
  if(typeof DecompressionStream==='function'){
    const data=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Uint8Array(await new Response(data).arrayBuffer());
  }
  const {gunzipSync}=await import('./assets/fflate.module.js');return gunzipSync(bytes);
}
async function readAsset(){
  const embedded=document.getElementById('aquila-embedded-glb');
  let bytes;
  if(embedded){
    const encoded=embedded.textContent.trim(),binary=atob(encoded);bytes=new Uint8Array(binary.length);
    for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
    embedded.remove();
  }else{
    const response=await fetch('./assets/aquila-metal.glb.gz');
    if(!response.ok)throw new Error('Model request '+response.status);
    bytes=new Uint8Array(await response.arrayBuffer());
  }
  const raw=await inflate(bytes);
  const {scene,animations}=await new GLTFLoader().parseAsync(raw.buffer,'');
  const clip=animations.find(action=>action.name===landing.name);
  if(!clip)throw new Error('The eagle landing performance is missing.');
  return {scene,clip,download:async()=>new Blob([await inflate(bytes)],{type:'model/gltf-binary'})};
}

// Bind all rigid pieces to their original hinges with one draw per material and system.
function skinBatches(scene,nodes){
  const boneList=[...nodes.values()],boneIndex=new Map(boneList.map((n,i)=>[n,i]));
  for(const joint of boneList){joint.quaternion.identity();joint.scale.set(1,1,1)}
  scene.updateMatrixWorld(true);
  const work=new Map(),old=new Set(),shellMaterials=new Map(),counts=Array(8).fill(0);
  scene.traverse(n=>{
    if(Number.isInteger(n.userData.partCount)&&n.userData.assembly>=0)counts[n.userData.assembly]+=n.userData.partCount;
    if(!n.isMesh)return;
    let marker=n,bone=n;
    while(marker&&!Number.isInteger(marker.userData.assembly))marker=marker.parent;
    while(bone&&!boneIndex.has(bone))bone=bone.parent;
    if(!marker||!bone)throw new Error('Unbound Blender component '+n.name);
    const id=marker.userData.assembly,shell=!!marker.userData.shell;
    const mat=n.material,g=n.geometry,hasTangents=!!g.attributes.tangent;
    const key=[mat.uuid,id,+shell,+hasTangents].join('.');
    if(!work.has(key))work.set(key,{id,shell,mat,hasTangents,items:[],vertices:0,tris:0});
    const batch=work.get(key);
    batch.items.push({part:n,bone:boneIndex.get(bone)});batch.vertices+=g.attributes.position.count;
    batch.tris+=g.index?.count??g.attributes.position.count;old.add(n);
  });
  const skeleton=new T.Skeleton(boneList),models=[],support=[];
  const v=new T.Vector3(),normalMatrix=new T.Matrix3();
  for(const entry of work.values()){
    const N=entry.vertices,positions=new Float32Array(N*3),normals=new Float32Array(N*3),
      uv=new Float32Array(N*2),colors=new Float32Array(N*3),
      tangents=entry.hasTangents?new Float32Array(N*4):null,
      skinIndices=new Uint16Array(N*4),skinWeights=new Float32Array(N*4),
      indices=N>65535?new Uint32Array(entry.tris):new Uint16Array(entry.tris);
    let vBase=0,iBase=0;
    for(const {part,bone} of entry.items){
      const g=part.geometry,a=g.attributes,m=part.matrixWorld;
      normalMatrix.getNormalMatrix(m);
      const handedness=m.determinant()<0?-1:1;
      for(let j=0;j<a.position.count;j++){
        const k=vBase+j;v.fromBufferAttribute(a.position,j).applyMatrix4(m).toArray(positions,k*3);
        v.fromBufferAttribute(a.normal,j).applyNormalMatrix(normalMatrix).toArray(normals,k*3);
        if(tangents){
          v.fromBufferAttribute(a.tangent,j).transformDirection(m).toArray(tangents,k*4);
          tangents[k*4+3]=a.tangent.getW(j)*handedness;
        }
        if(a.uv){uv[k*2]=a.uv.getX(j);uv[k*2+1]=a.uv.getY(j)}
        if(a.color){colors[k*3]=a.color.getX(j);colors[k*3+1]=a.color.getY(j);colors[k*3+2]=a.color.getZ(j)}
        else colors[k*3]=colors[k*3+1]=colors[k*3+2]=1;
        skinIndices[k*4]=bone;skinWeights[k*4]=1;
      }
      const src=g.index;const indexCount=src?.count??a.position.count;
      for(let j=0;j<indexCount;j++)indices[iBase+j]=vBase+(src?src.getX(j):j);
      iBase+=indexCount;vBase+=a.position.count;
    }
    const geo=new T.BufferGeometry();
    for(const [key,array,size] of [['position',positions,3],['normal',normals,3],['uv',uv,2],['color',colors,3],['skinIndex',skinIndices,4],['skinWeight',skinWeights,4]])
      geo.setAttribute(key,new T.BufferAttribute(array,size));
    if(tangents)geo.setAttribute('tangent',new T.BufferAttribute(tangents,4));
    geo.setIndex(new T.BufferAttribute(indices,1));
    let mat=entry.mat;
    if(entry.shell){
      if(!shellMaterials.has(mat))shellMaterials.set(mat,mat.clone());
      mat=shellMaterials.get(mat);
    }
    mat.vertexColors=true;mat.side=T.FrontSide;
    const mesh=new T.SkinnedMesh(geo,mat);mesh.name='Assembly '+entry.id+' · '+mat.name;
    mesh.bind(skeleton,new T.Matrix4());mesh.frustumCulled=false;
    mesh.boundingSphere=new T.Sphere(new T.Vector3(),18);mesh.userData.assembly=entry.id;mesh.userData.shell=entry.shell;
    mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);
    if(entry.id<0)support.push(mesh);else models.push(mesh);
  }
  const removedGeometry=new Set();
  for(const part of old){part.removeFromParent();removedGeometry.add(part.geometry)}
  for(const g of removedGeometry)g.dispose();
  return {models,support,shellMaterials,counts};
}
export async function loadEagle(){
  const {scene:root,clip,download}=await readAsset(),nodes=new Map();
  root.traverse(n=>{if(n.userData.joint)nodes.set(n.userData.joint,n)});
  if(!nodes.has('head')||!nodes.has('wrist.L')||!nodes.has('wrist.R'))throw Error('Incomplete eagle rig');
  const {models,support,shellMaterials,counts}=skinBatches(root,nodes);
  if(counts.some((v,i)=>v!==rig.counts[i]))throw new Error('Part register mismatch '+counts.join(','));
  const keys=Object.keys(rig.poses);
  const tracks=new Map();
  for(const track of clip.tracks){
    const binding=T.PropertyBinding.parseTrackName(track.name);
    const joint=T.PropertyBinding.findNode(root,binding.nodeName)?.userData.joint;
    if(!joint)throw Error('Unbound flight track '+track.name);
    if(!tracks.has(joint))tracks.set(joint,{});
    tracks.get(joint)[binding.propertyName]=track.createInterpolant();
  }
  const hinges=[...nodes].map(([name,node])=>{
    let p=node,wing=0;
    while(p){if(p.userData.joint?.startsWith('wing.')){wing=p.userData.joint.endsWith('.L')?-1:1;break}p=p.parent}
    return {name,node,rest:node.position.clone(),wing,tracks:tracks.get(name),
      presets:Object.fromEntries(keys.map(k=>[k,new T.Quaternion().fromArray(rig.poses[k][name])]))};
  });
  const marks=markSpecs.map(([key,p])=>[nodes.get(key),new T.Vector3(...p)]);
  const blinkAxis={L:wv(-.47,.8827,0).normalize(),R:wv(.47,.8827,0).normalize()};
  const angleQ=new T.Quaternion();let preset='front',cutaway=false,previous=null;
  function pose({flightTime=null,spread=1,headTurn=0,blink=0,flap=0,transition=1}={}){
    const blend=smooth(transition,0,1);
    for(const h of hinges){
      const {name,node,rest,wing,presets}=h;
      const sampled=flightTime!==null&&preset==='front'?h.tracks:null;
      if(sampled?.position)node.position.fromArray(sampled.position.evaluate(flightTime));
      else node.position.copy(rest);
      if(sampled?.quaternion)node.quaternion.fromArray(sampled.quaternion.evaluate(flightTime));
      else node.quaternion.copy(presets[preset]);
      if(wing){
        const target=preset==='perched'||spread>1?'front':'perched';
        node.quaternion.slerp(presets[target],Math.abs(1-spread));
        if(name.startsWith('wing.')||name.startsWith('wrist.'))node.quaternion.multiply(angleQ.setFromAxisAngle(axisZ,wing*flap*(name[0]==='w'&&name[1]==='i'?.18:.07)));
      }
      if(name==='head')node.quaternion.multiply(angleQ.setFromAxisAngle(axisY,headTurn));
      if(name.startsWith('lid.')){const lr=name.slice(-1);node.quaternion.multiply(angleQ.setFromAxisAngle(blinkAxis[lr],(lr==='L'?-1:1)*1.54*blink))}
      if(previous&&blend<1){node.quaternion.slerpQuaternions(h.fromQ,node.quaternion,blend);node.position.lerpVectors(h.fromP,node.position,blend)}
    }
    const standScale=previous?T.MathUtils.lerp(previous.stand,preset==='perched'?1:.00001,blend):(preset==='perched'?1:.00001);
    nodes.get('stand').scale.setScalar(standScale);for(const m of support)m.visible=standScale>.001;
    if(blend===1)previous=null;
    root.updateMatrixWorld(true);
  }
  function xray(on){
    cutaway=on;for(const mesh of models)mesh.castShadow=!on||!mesh.userData.shell;
    for(const m of shellMaterials.values()){
      m.transparent=on;m.opacity=on?.17:1;m.depthWrite=!on;m.needsUpdate=true;
    }
  }
  function setPreset(value,animate=false){
    if(animate){
      for(const h of hinges){(h.fromQ??=new T.Quaternion()).copy(h.node.quaternion);(h.fromP??=new T.Vector3()).copy(h.node.position)}
      previous={stand:nodes.get('stand').scale.x};
    }else previous=null;
    preset=value;pose({transition:animate?0:1});
  }
  function focus(id,out){const [node,p]=marks[id]??marks[4];return node.localToWorld(out.copy(p))}
  const shoulderPoint=new T.Vector3(),armVector=new T.Vector3();
  function driveReadout(out){
    nodes.get('wing.R').getWorldPosition(shoulderPoint);
    nodes.get('elbow.R').getWorldPosition(armVector).sub(shoulderPoint);
    out.wing=T.MathUtils.radToDeg(Math.atan2(armVector.y,Math.hypot(armVector.x,armVector.z)));
    armVector.set(0,0,1).applyQuaternion(nodes.get('head').quaternion);
    out.yaw=T.MathUtils.radToDeg(Math.atan2(armVector.x,armVector.z));
  }
  function fit(view='hero'){return rig.frames[preset][view]??rig.frames[preset].hero}
  setPreset('front');
  return {root,download,count:counts.reduce((n,v)=>n+v,0),counts,pickables:models,pose,setPreset,xray,focus,fit,driveReadout,
    flightOrigin:nodes.get('bird').position,feet:[nodes.get('foot.L'),nodes.get('foot.R')],
    get ground(){return rig.frames[preset].ground},get cutaway(){return cutaway}};
}
