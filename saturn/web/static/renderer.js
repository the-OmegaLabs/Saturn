export class Renderer {
  constructor(send, notice) {
    this.send=send; this.notice=notice; this.canvas=document.querySelector('#canvas');
    this.ctx=this.canvas.getContext('2d'); this.layer=document.querySelector('#controls');
    this.overlayCanvas=document.createElement('canvas');this.overlayCanvas.id='overlay-canvas';this.overlayCanvas.setAttribute('aria-hidden','true');this.canvas.after(this.overlayCanvas);this.overlayCtx=this.overlayCanvas.getContext('2d');
    this.scene={nodes:{},order:[]}; this.elements=new Map(); this.scroll=new Map();
    this.fonts=new Map(); this.images=new Map(); this.animations=new Map(); this.frame=0;
    this.layer.addEventListener('wheel',e=>this.wheel(e),{passive:false});
    this.canvas.addEventListener('wheel',e=>this.wheel(e),{passive:false});
  }
  update(scene) {
    const old=this.scene; this.scene=scene;
    for(const id of scene.order){
      const n=scene.nodes[id],prev=old.nodes[id];
      if(prev && n.animation && prev.opacity!==n.opacity) {
        this.animations.set(id,{from:this.opacity(prev),to:n.opacity,start:performance.now(),duration:n.animation.duration,curve:n.animation.curve});
      }
      if(n.kind==='scroll') this.scroll.set(id,Math.max(0,Math.min(Math.max(0,n.content_size-n.bounds[n.horizontal?2:3]),this.scroll.get(id)??n.offset??0)));
    }
    for(const [id,el] of this.elements) if(!scene.nodes[id]){el.remove();this.elements.delete(id);this.animations.delete(id);}
    for(const id of this.scroll.keys()) if(!scene.nodes[id]) this.scroll.delete(id);
    for(const [family,resource] of Object.entries(scene.fonts||{})) if(!this.fonts.has(family)){
      const face=new FontFace(family,`url(${new URL('../resources/'+resource,import.meta.url)})`,family==='SaturnDefault'?{weight:'100 900'}:{});
      this.fonts.set(family,face.load().then(f=>{document.fonts.add(f);this.request();}).catch(e=>this.notice('Font load failed: '+e.message)));
    }
    document.title=scene.title; document.body.style.background=scene.background;
    this.syncElements(); this.request();
    if(scene.focus && old.focus!==scene.focus) this.elements.get(scene.focus)?.focus();
  }
  bounds(n) {
    const b=[...n.bounds]; for(const [id,horizontal] of n.scrollers||[]) b[horizontal?0:1]-=this.scroll.get(id)||0;
    return b;
  }
  clip(n) {
    let result=null;
    for(let i=0;i<(n.clips||[]).length;i++){
      const c=[...n.clips[i]];
      for(const [id,horizontal] of (n.scrollers||[]).slice(0,i)) c[horizontal?0:1]-=this.scroll.get(id)||0;
      if(!result)result=c;else{const right=Math.min(result[0]+result[2],c[0]+c[2]),bottom=Math.min(result[1]+result[3],c[1]+c[3]);result=[Math.max(result[0],c[0]),Math.max(result[1],c[1]),0,0];result[2]=Math.max(0,right-result[0]);result[3]=Math.max(0,bottom-result[1]);}
    }
    return result;
  }
  opacity(n) {
    const a=this.animations.get(n.id); if(!a)return n.opacity;
    let t=Math.min(1,(performance.now()-a.start)/Math.max(1,a.duration));
    if(t===1){this.animations.delete(n.id);return a.to;}
    if(a.curve!=='linear')t=t*t*(3-2*t);
    return a.from+(a.to-a.from)*t;
  }
  request(){if(!this.frame)this.frame=requestAnimationFrame(()=>{this.frame=0;this.draw();});}
  draw(){
    const ratio=Math.min(4,devicePixelRatio||1),w=innerWidth,h=innerHeight;
    for(const canvas of [this.canvas,this.overlayCanvas]){if(canvas.width!==Math.round(w*ratio)||canvas.height!==Math.round(h*ratio)){canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);canvas.style.width=w+'px';canvas.style.height=h+'px';}const c=canvas.getContext('2d');c.setTransform(ratio,0,0,ratio,0,0);c.clearRect(0,0,w,h);}
    const firstOverlay=this.scene.order.findIndex(id=>this.scene.nodes[id].overlay);this.overlayCanvas.hidden=firstOverlay<0;this.overlayCanvas.style.zIndex=firstOverlay+1;
    for(const id of this.scene.order){const n=this.scene.nodes[id],b=this.bounds(n),clip=this.clip(n);if(b[2]<=0||b[3]<=0)continue;
      const c=n.overlay?this.overlayCtx:this.ctx;
      c.save();c.globalAlpha=Math.max(0,Math.min(1,this.opacity(n)))*(n.disabled?.5:1);
      if(clip){c.beginPath();c.rect(...clip);c.clip();}
      if(n.kind==='rect'||n.kind==='button'||n.kind==='barrier'){c.beginPath();c.roundRect(...b,Math.min(n.radius||0,b[2]/2,b[3]/2));c.fillStyle=n.background;c.fill();if(n.border){c.strokeStyle=n.border;c.stroke();}}
      if(n.kind==='text'||n.kind==='button'){
        c.font=`${n.italic?'italic ':''}${n.weight||400} ${n.size}px ${n.font}`;c.fillStyle=n.color;c.textBaseline='middle';
        if(n.kind==='button'){c.textAlign='center';const labelWidth=c.measureText(n.text).width,total=labelWidth+(n.icon?n.icon_size+(n.text?n.icon_gap:0):0);c.fillText(n.text,b[0]+b[2]/2+(n.icon?(n.icon_size+n.icon_gap)/2:0),b[1]+b[3]/2);if(n.icon){c.font=`${n.icon_size}px ${n.icon_font}`;c.fillText(n.icon,b[0]+(b[2]-total)/2+n.icon_size/2,b[1]+b[3]/2);}}
        else{c.textAlign=n.align==='center'?'center':n.align==='end'||n.align==='right'?'right':'left';const x=b[0]+(c.textAlign==='center'?b[2]/2:c.textAlign==='right'?b[2]:0);for(let i=0;i<n.lines.length;i++)c.fillText(n.lines[i],x,b[1]+n.line_height*(i+.5));}
      }
      if(n.kind==='icon'){c.font=`${n.icon_size}px ${n.icon_font}`;c.fillStyle=n.color;c.textAlign='center';c.textBaseline='middle';c.fillText(n.icon,b[0]+b[2]/2,b[1]+b[3]/2);}
      if(n.kind==='progress'){const v=n.value==null?.3:Math.max(0,Math.min(1,n.value));c.lineWidth=n.stroke;c.strokeStyle=n.background;if(n.circular){const radius=Math.max(0,(Math.min(b[2],b[3])-n.stroke)/2);c.beginPath();c.arc(b[0]+b[2]/2,b[1]+b[3]/2,radius,0,Math.PI*2);c.stroke();c.strokeStyle=n.color;c.lineCap='round';const start=-Math.PI/2+(n.value==null?performance.now()/500:0);c.beginPath();c.arc(b[0]+b[2]/2,b[1]+b[3]/2,radius,start,start+Math.PI*2*v);c.stroke();}else{c.fillStyle=n.background;c.fillRect(...b);c.fillStyle=n.color;c.fillRect(b[0],b[1],b[2]*v,b[3]);}}
      if(n.kind==='image'){let img=this.images.get(n.resource);if(!img){img=new Image();img.src=new URL('../resources/'+n.resource,import.meta.url);img.onload=()=>this.request();this.images.set(n.resource,img);}if(img.complete&&img.naturalWidth){let drawable=img;if(n.tint){const key=n.resource+'|'+n.tint;if(!this.images.has(key)){const tint=document.createElement('canvas');tint.width=img.naturalWidth;tint.height=img.naturalHeight;const tc=tint.getContext('2d');tc.drawImage(img,0,0);tc.globalCompositeOperation='source-in';tc.fillStyle=n.tint;tc.fillRect(0,0,tint.width,tint.height);this.images.set(key,tint);}drawable=this.images.get(key);}c.beginPath();c.roundRect(...b,n.radius||0);c.clip();let dw=b[2],dh=b[3];if(n.fit!=='fill'){let scale=n.fit==='cover'?Math.max(dw/img.naturalWidth,dh/img.naturalHeight):Math.min(dw/img.naturalWidth,dh/img.naturalHeight);if(n.fit==='none')scale=1;else if(n.fit==='scaleDown')scale=Math.min(1,scale);else if(n.fit==='fitWidth')scale=dw/img.naturalWidth;else if(n.fit==='fitHeight')scale=dh/img.naturalHeight;dw=img.naturalWidth*scale;dh=img.naturalHeight*scale;}c.drawImage(drawable,b[0]+(b[2]-dw)/2,b[1]+(b[3]-dh)/2,dw,dh);}}
      c.restore();
    }
    this.positionElements();if(this.animations.size||this.scene.order.some(id=>this.scene.nodes[id].kind==='progress'&&this.scene.nodes[id].value==null))this.request();
  }
  event(n,name,value,extra={}){this.send({type:'event',id:crypto.randomUUID(),control:n.id,name,value,...extra});}
  resetInteraction(){
    this.scroll.clear();this.animations.clear();
    for(const el of this.elements.values())if(el._edit){clearTimeout(el._edit.timer);el._edit={version:0,pending:0,revision:0,composing:false,generation:0,sent:0,draft:false};}
  }
  syncElements(){
    for(const id of this.scene.order){const n=this.scene.nodes[id];let el=this.elements.get(id);
      if(n.kind==='input'){
        if(el && ((el.tagName==='TEXTAREA')!==!!n.multiline)){el.remove();this.elements.delete(id);el=null;}
        if(!el){el=document.createElement(n.multiline?'textarea':'input');el.className='field';el._edit={version:0,pending:0,revision:n.input_revision,composing:false};
          const flush=()=>{const node=this.scene.nodes[id];if(!node)return;clearTimeout(el._edit.timer);if(el._edit.composing||el._edit.sent===el._edit.generation)return;el._edit.sent=el._edit.generation;const v=++el._edit.version;el._edit.pending=v;this.event(node,'change',el.value,{version:v,input_revision:el._edit.revision});};
          el.addEventListener('compositionstart',()=>{el._edit.composing=true;clearTimeout(el._edit.timer);});
          el.addEventListener('compositionend',()=>{el._edit.composing=false;flush();});
          el._edit.generation=el._edit.sent=0;
          el.addEventListener('input',()=>{el._edit.generation++;el._edit.draft=true;if(!el._edit.composing)el._edit.timer=setTimeout(flush,60);});
          el.addEventListener('focus',()=>this.event(this.scene.nodes[id],'focus'));
          el.addEventListener('blur',()=>{if(el._edit.draft&&!el._edit.composing)flush();this.event(this.scene.nodes[id],'blur');});
          el.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.isComposing&&!this.scene.nodes[id].multiline){if(el._edit.draft)flush();this.event(this.scene.nodes[id],'submit');}});
          el.value=n.value;this.layer.append(el);this.elements.set(id,el);
        }
        if(!n.multiline)el.type=n.password?'password':'text';el.placeholder=n.placeholder||n.label||'';el.setAttribute('aria-label',n.label||n.placeholder||'Text input');el.readOnly=n.read_only;
        if(n.max_length!=null&&n.max_length>=0)el.maxLength=n.max_length;else el.removeAttribute('maxlength');
        el._edit.revision=Math.max(el._edit.revision,n.input_revision);
        if(!el._edit.pending&&!el._edit.draft&&!el._edit.composing&&el.value!==n.value)this.assignValue(el,n.value);
        Object.assign(el.style,{fontSize:n.size+'px',fontFamily:n.font,color:n.color,background:n.background,border:`1px solid ${n.border}`,borderRadius:n.radius+'px'});
      } else if(n.kind==='slider'){
        if(!el){el=document.createElement('input');el.type='range';el.className='value-slider';el.addEventListener('input',()=>this.event(this.scene.nodes[id],'change',+el.value));el.addEventListener('pointerdown',()=>{el._dragging=true;this.event(this.scene.nodes[id],'change_start',+el.value);});el.addEventListener('pointerup',()=>{el._dragging=false;this.event(this.scene.nodes[id],'change_end',+el.value);});el.addEventListener('pointercancel',()=>{el._dragging=false;});this.layer.append(el);this.elements.set(id,el);}el.min=n.minimum;el.max=n.maximum;el.step=n.step;if(!el._dragging)el.value=n.value;el.setAttribute('aria-label',n.label);el.style.accentColor=n.color;
      } else if(n.kind==='select'){
        if(!el){el=document.createElement('select');el.className='select-field';el.addEventListener('change',()=>{const node=this.scene.nodes[id],index=+el.value;if(Number.isInteger(index)&&node.options[index])this.event(node,'select',node.options[index].key);});this.layer.append(el);this.elements.set(id,el);}
        const key=JSON.stringify([n.placeholder,n.options]);if(key!==el._optionsKey){el.replaceChildren();const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent=n.placeholder;placeholder.disabled=true;el.append(placeholder);n.options.forEach((o,i)=>{const option=document.createElement('option');option.value=i;option.textContent=o.text;option.disabled=o.disabled;el.append(option);});el._optionsKey=key;}const index=n.options.findIndex(o=>o.key===n.value);el.value=index<0?'':String(index);el.setAttribute('aria-label',n.label);Object.assign(el.style,{fontSize:n.size+'px',fontFamily:n.font,color:n.color,background:n.background,border:`1px solid ${n.border}`});
      } else if(n.block_pointer||(n.kind==='barrier'&&!n.clickable)){
        if(!el){el=document.createElement('div');if(n.block_pointer){el.setAttribute('role','dialog');el.setAttribute('aria-modal','true');}this.layer.append(el);this.elements.set(id,el);}if(n.block_pointer)el.setAttribute('aria-label',n.dialog_title||'Dialog');
      } else if(n.kind==='text'){
        if(!el){el=document.createElement('span');el.style.pointerEvents='none';el.style.color='transparent';this.layer.append(el);this.elements.set(id,el);}el.textContent=n.text;el.style.fontSize=n.size+'px';el.style.fontFamily=n.font;el.style.whiteSpace='pre';el.style.lineHeight=n.line_height+'px';
      } else if(n.kind==='toggle'){
        if(!el){el=document.createElement('label');el.className='toggle';const input=document.createElement('input');input.type='checkbox';input.addEventListener('change',()=>this.event(this.scene.nodes[id],'change',input.checked));el.append(input,document.createElement('span'));this.layer.append(el);this.elements.set(id,el);}
        el.firstChild.checked=n.value;el.firstChild.disabled=n.disabled;el.firstChild.className=n.toggle_type==='switch'?'switch-input':'';el.firstChild.setAttribute('role',n.toggle_type==='switch'?'switch':'checkbox');el.lastChild.textContent=n.label;el.style.color=n.color;el.style.fontFamily=n.font;el.style.fontSize=n.size+'px';el.style.whiteSpace='nowrap';el.firstChild.style.flexShrink=0;
      } else if(n.clickable){
        if(!el){el=document.createElement('button');el.addEventListener('click',()=>{const node=this.scene.nodes[id];this.event(node,node.kind==='barrier'?'dismiss':'click');});this.layer.append(el);this.elements.set(id,el);}el.textContent=n.text||'';el.setAttribute('aria-label',n.aria_label||n.text||'Action');
      } else if(n.kind==='scroll'){
        if(!el){el=document.createElement('div');el.className='scrollbar';el.setAttribute('role','scrollbar');el.setAttribute('aria-label','Scroll list');el.append(document.createElement('div'));el.firstChild.className='scroll-thumb';
          el.addEventListener('keydown',e=>{const node=this.scene.nodes[id],extent=node.bounds[node.horizontal?2:3],offset=this.scroll.get(id)||0;let value;if(e.key==='Home')value=0;else if(e.key==='End')value=node.content_size;else if(e.key==='PageDown')value=offset+extent;else if(e.key==='PageUp')value=offset-extent;else if(e.key==='ArrowDown'||e.key==='ArrowRight')value=offset+32;else if(e.key==='ArrowUp'||e.key==='ArrowLeft')value=offset-32;if(value!==undefined){e.preventDefault();this.setScroll(node,value);}});
          el.addEventListener('pointerdown',e=>{const node=this.scene.nodes[id];if(node.disabled)return;el.focus();const thumb=el.firstChild.getBoundingClientRect(),coordinate=node.horizontal?e.clientX:e.clientY,start=node.horizontal?thumb.left:thumb.top;if(e.target!==el.firstChild){this.setScroll(node,(this.scroll.get(id)||0)+(coordinate<start?-1:1)*node.bounds[node.horizontal?2:3]);return;}el._drag={grab:coordinate-start};el.setPointerCapture(e.pointerId);e.preventDefault();});
          el.addEventListener('pointermove',e=>{if(!el._drag)return;const node=this.scene.nodes[id],track=el.getBoundingClientRect(),thumb=el.firstChild.getBoundingClientRect(),extent=node.horizontal?track.width:track.height,travel=extent-(node.horizontal?thumb.width:thumb.height),position=(node.horizontal?e.clientX-track.left:e.clientY-track.top)-el._drag.grab;if(travel>0)this.setScroll(node,position/travel*Math.max(0,node.content_size-extent));});
          const release=()=>{el._drag=null;};el.addEventListener('pointerup',release);el.addEventListener('lostpointercapture',release);this.layer.append(el);this.elements.set(id,el);}
        const maximum=Math.max(0,n.content_size-n.bounds[n.horizontal?2:3]);el.hidden=maximum===0;el.tabIndex=n.disabled?-1:0;el.setAttribute('aria-valuemin','0');el.setAttribute('aria-valuemax',maximum);el.setAttribute('aria-orientation',n.horizontal?'horizontal':'vertical');el.setAttribute('aria-disabled',n.disabled);
      }
      if(el && n.kind!=='toggle'&&n.kind!=='scroll')el.disabled=n.disabled;
    }
    this.positionElements();
  }
  assignValue(el,value){const start=el.selectionStart,end=el.selectionEnd,direction=el.selectionDirection;el.value=value;if(document.activeElement===el&&start!=null)el.setSelectionRange(Math.min(start,value.length),Math.min(end,value.length),direction);}
  ack(message){const el=this.elements.get(message.control);if(!el?._edit)return;const state=el._edit;state.revision=Math.max(state.revision,message.input_revision??state.revision);
    if(message.version===state.pending){state.pending=0;if(!state.composing&&state.sent===state.generation){state.draft=false;this.assignValue(el,message.value??el.value);if(message.conflict)this.notice('Another view changed this field; its value was kept.');}}
  }
  positionElements(){for(const [id,el] of this.elements){const n=this.scene.nodes[id];if(!n)continue;let b=this.bounds(n);if(n.kind==='scroll'){const extent=b[n.horizontal?2:3],maximum=Math.max(0,n.content_size-extent),size=Math.min(extent,Math.max(18,extent*extent/Math.max(1,n.content_size))),position=maximum?(extent-size)*(this.scroll.get(id)||0)/maximum:0;b=n.horizontal?[b[0],b[1]+b[3]-12,b[2],12]:[b[0]+b[2]-12,b[1],12,b[3]];Object.assign(el.firstChild.style,n.horizontal?{left:position+'px',top:'3px',width:size+'px',height:'6px'}:{left:'3px',top:position+'px',width:'6px',height:size+'px'});el.setAttribute('aria-valuenow',Math.round(this.scroll.get(id)||0));}
    Object.assign(el.style,{left:b[0]+'px',top:b[1]+'px',width:Math.max(0,b[2])+'px',height:Math.max(0,b[3])+'px',opacity:this.opacity(n),zIndex:this.scene.order.indexOf(id)+1});
    const clip=this.clip(n);el.style.clipPath=clip?`inset(${Math.max(0,clip[1]-b[1])}px ${Math.max(0,b[0]+b[2]-clip[0]-clip[2])}px ${Math.max(0,b[1]+b[3]-clip[1]-clip[3])}px ${Math.max(0,clip[0]-b[0])}px)`:'none';
  }}
  setScroll(n,value){if(n.disabled)return;const extent=n.bounds[n.horizontal?2:3],v=Math.max(0,Math.min(Math.max(0,n.content_size-extent),value));this.scroll.set(n.id,v);this.request();clearTimeout(n._timer);n._timer=setTimeout(()=>this.send({type:'scroll',control:n.id,offset:v}),30);}
  wheel(e){const n=[...this.scene.order].reverse().map(id=>this.scene.nodes[id]).find(n=>{if(n.kind!=='scroll')return false;const b=this.bounds(n);return e.clientX>=b[0]&&e.clientX<b[0]+b[2]&&e.clientY>=b[1]&&e.clientY<b[1]+b[3];});if(n){e.preventDefault();this.setScroll(n,(this.scroll.get(n.id)||0)+(e.deltaMode===1?e.deltaY*20:e.deltaY));}}
}
