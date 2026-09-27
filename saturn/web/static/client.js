import {Renderer} from './renderer.js';
const status=document.querySelector('#status');let socket,revision=0,resume=null,delay=500,resizeTimer,stopped=false;
const notice=value=>{status.textContent=value;};
const send=message=>{if(socket?.readyState===WebSocket.OPEN)socket.send(JSON.stringify(message));};
const renderer=new Renderer(send,notice);
const controls=document.querySelector('#controls');controls.inert=true;
const viewport=()=>({width:innerWidth,height:innerHeight,density:devicePixelRatio||1});
function connect(){
  const url=new URL('../ws',import.meta.url);url.protocol=location.protocol==='https:'?'wss:':'ws:';url.search=location.search;
  socket=new WebSocket(url);
  socket.onopen=()=>{send({type:'hello',protocol:1,...viewport(),resume});};
  socket.onmessage=event=>{
    const m=JSON.parse(event.data);
    if(m.type==='welcome'){resume=m.resume;delay=500;notice('');renderer.resetInteraction();document.documentElement.dataset.session=m.session;document.documentElement.dataset.client=m.client_id;return;}
    if(m.type==='error'){notice(m.error);if(m.reconnect)socket.close();return;}
    if(m.type==='ack'){renderer.ack(m);return;}
    if(m.type==='snapshot'){revision=m.revision;renderer.update(m.scene);controls.inert=false;}
    else if(m.type==='patch'){
      if(m.base_revision!==revision){send({type:'resync',...viewport()});return;}
      const scene={...renderer.scene,...m.metadata,nodes:{...renderer.scene.nodes}};
      for(const op of m.ops){if(op.op==='remove')delete scene.nodes[op.id];else scene.nodes[op.node.id]=op.node;}
      revision=m.revision;renderer.update(scene);
    }
    if((m.type==='snapshot'||m.type==='patch')&&renderer.scene.route!==decodeURIComponent(location.hash.slice(1)||'/'))history.replaceState(null,'','#'+encodeURIComponent(renderer.scene.route));
  };
  socket.onclose=e=>{controls.inert=true;if(stopped)return;notice(e.code===1008?'Connection refused. Reload after checking the application.':'Reconnecting…');if(e.code!==1008){setTimeout(connect,delay);delay=Math.min(10000,delay*2);}};
}
addEventListener('resize',()=>{renderer.request();clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>send({type:'resize',...viewport()}),60);});
addEventListener('hashchange',()=>send({type:'route',route:decodeURIComponent(location.hash.slice(1)||'/')}));
addEventListener('pagehide',()=>{stopped=true;socket?.close();});
addEventListener('pageshow',e=>{if(e.persisted){stopped=false;connect();}});
connect();
