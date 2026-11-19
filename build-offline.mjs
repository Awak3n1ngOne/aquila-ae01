import {readFile,writeFile,rename} from 'node:fs/promises';
import {resolve,basename} from 'node:path';
const output=process.argv[2];if(!output)throw Error('Pass the destination HTML path.');
const dist=new URL('./dist/',import.meta.url),load=(f)=>readFile(new URL(f,dist),'utf8');
const modules=['assets/three.module.js','assets/OrbitControls.js','assets/fflate.module.js',
  'assets/addons/loaders/GLTFLoader.js','assets/addons/utils/BufferGeometryUtils.js','assets/aquila-rig.js','solid-rig.js','studio-prints.js','app.js'];
const names=new Map(modules.map(path=>[basename(path),'aquila/'+basename(path)]));
const encoded=(type,bytes)=>'data:'+type+';base64,'+Buffer.from(bytes).toString('base64');
function localImports(source){
  return source.replace(/((?:from\s+|\bimport\(\s*)['"])(\.\.?\/[^'"]+\.js)(['"])/g,(match,open,path,close)=>{
    const name=names.get(basename(path));if(!name)throw Error('Unknown offline module '+path);
    return open+name+close;
  });
}
const imports={};
for(const f of modules)imports[names.get(basename(f))]=encoded('text/javascript',localImports(await load(f)));
let style=await load('style.css');
for(const f of new Set(style.match(/\.\/assets\/[a-z-]+\.(?:png|webp|svg)/g))){
  const mime=f.endsWith('.svg')?'image/svg+xml':'image/'+f.split('.').pop();
  const u=encoded(mime,await readFile(new URL(f,dist)));style=style.replaceAll(f,u);
}
let html=await load('index.html');
for(const ref of new Set(html.match(/\.\/assets\/(?:prints\/[a-z]+\.webp|studio-radiance\.png)/g))){
  const bytes=await readFile(new URL(ref,dist));html=html.replaceAll(ref,encoded(ref.endsWith('.png')?'image/png':'image/webp',bytes));
}
const app=localImports(await load('boot.js'));
const glb=await readFile(new URL('assets/aquila-metal.glb.gz',dist));
html=html.replace(/<link rel="preload" as="fetch"[^>]+>\s*/,'')
  .replace('<link rel="stylesheet" href="style.css">',()=>'<style>'+style+'</style>')
  .replace('<script type="module" src="boot.js"></script>',()=>'<script id="aquila-embedded-glb" type="application/octet-stream">'+glb.toString('base64')+
      '</script>\n<script type="importmap">'+JSON.stringify({imports})+'</script>\n<script type="module">'+app+'</script>');
const dest=resolve(output),temp=dest+'.'+process.pid+'.tmp';
const notices=await Promise.all([load('../LICENSE'),load('assets/THIRD-PARTY-NOTICES.txt')]);
html+='\n<!--\n'+notices.join('\n\n')+'\n-->\n';
await writeFile(temp,html,'utf8');await rename(temp,dest);
console.log('Wrote '+dest+' ('+Buffer.byteLength(html)+' bytes)');
