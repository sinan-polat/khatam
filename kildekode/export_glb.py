import asyncio, base64, json
from playwright.async_api import async_playwright
CFG = {
 'bayt':    {'color':'smaragd','name':'Hassan','ar':'حسن'},
 'usra':    {'color':'smaragd','names':['Yusuf','Maryam','Adam','Sara'],'ars':['يوسف','مريم','آدم','سارة']},
 'eidiyya': {'color':'smaragd','name':'Sara','ar':'سارة'},
 'mubarak': {'color':'sort','greeting':'ramadan'},
 'maktaba': {'color':'sort','shelf':['seerah','quran','tafsir','hadith']},
 'tabaq':   {'color':'sort'},
 'gaveaeske': {'color':'sort','name':'Hassan','ar':'حسن','shelf':['quran','tafsir','hadith','fiqh']},
}
JS = r"""
async (args) => {
  const [id, cfg] = args;
  const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
  const THREE = await import('three');
  await document.fonts.load('800 100px Cairo'); await document.fonts.load('600 100px Poppins');
  let el = document.getElementById('xp'); if(!el){ el=document.createElement('div'); el.id='xp'; el.style.cssText='position:fixed;left:0;top:0;width:600px;height:600px'; document.body.appendChild(el); }
  K3D.mount(el, id, cfg);
  await new Promise(r=>setTimeout(r,400));
  const root = K3D.root.clone(true);
  // swap gold decals for a plain textured material (alpha mask in the colour map) so the exporter keeps it
  const src=[], dst=[]; K3D.root.traverse(o=>src.push(o)); root.traverse(o=>dst.push(o));
  dst.forEach((o,i)=>{ const s=src[i]; if(!o.isMesh) return;
    if(s.material.alphaMap){ o.material = new THREE.MeshStandardMaterial({ map: s.material.alphaMap, name:'GOLDDECAL' }); }
    else { const c='#'+s.material.color.getHexString(); const metal=s.material.metalness>0.5;
      o.material = new THREE.MeshStandardMaterial({ color: s.material.color, metalness: s.material.metalness, roughness: s.material.roughness, name: metal?('METAL_'+c):('PLA_'+c) }); } });
  root.updateMatrixWorld(true);
  const ab = await new GLTFExporter().parseAsync(root, { binary: true });
  let bin=''; const u=new Uint8Array(ab); for(let i=0;i<u.length;i+=0x8000) bin+=String.fromCharCode.apply(null,u.subarray(i,i+0x8000));
  return btoa(bin);
}"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        pg = await b.new_page(viewport={'width':1200,'height':900})
        pg.on('pageerror', lambda e: print('ERR', e)); pg.on('console', lambda m: print('LOG', m.text) if m.type=='error' else None)
        await pg.goto('http://localhost:8765/index.html#/p/bayt'); await pg.wait_for_function('window.K3D && K3D.ready', timeout=60000)
        for pid, cfg in CFG.items():
            data = await pg.evaluate(JS, [pid, cfg])
            open(f'glb/{pid}.glb','wb').write(base64.b64decode(data)); print(pid, len(data))
        await b.close()
asyncio.run(main())
