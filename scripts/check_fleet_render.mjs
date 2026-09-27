// Initial React render regression checks. Maps are stubbed; this is not browser testing.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const root = fileURLToPath(new URL('../',import.meta.url));
const require = createRequire(new URL('../government_portal/package.json',import.meta.url));
const { rolldown } = await import(pathToFileURL(require.resolve('rolldown')));
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { MemoryRouter } = require('react-router-dom');
const entry = '\0render-check', maps = '\0map-stub', css = '\0css-stub';
const bundle = await rolldown({input:entry, platform:'node', transform:{jsx:'react-jsx',define:{'import.meta.env':'{}'}}, plugins:[{
  name:'isolated-render-check',
  resolveId(source) {
    if ([entry,maps,css].includes(source)) return source;
    if (source.startsWith('node:')) return {id:source,external:true};
    if (source.endsWith('.css')) return css;
    if (source==='react-leaflet') return maps;
    if (!source.startsWith('.') && !path.isAbsolute(source)) return {id:pathToFileURL(require.resolve(source)).href,external:true};
  },
  load(id) {
    if (id===entry) return `export {default as FleetPage} from ${JSON.stringify(path.join(root,'government_portal/src/pages/FleetPage.jsx'))};
      export {default as RoutePlanner} from ${JSON.stringify(path.join(root,'user_portal/src/pages/RoutePlanner.jsx'))};
      export {default as LiveCameraPanel} from ${JSON.stringify(path.join(root,'government_portal/src/components/LiveCameraPanel.jsx'))};
      export * from ${JSON.stringify(path.join(root,'shared/routeAlerts.js'))};
      export {default as GovernmentLayout} from ${JSON.stringify(path.join(root,'government_portal/src/App.jsx'))};
      export {default as GovernmentRoute} from ${JSON.stringify(path.join(root,'user_portal/src/components/GovernmentRoute.jsx'))};`;
    if (id===css) return '';
    if (id===maps) return `export const MapContainer=({children})=>children, CircleMarker=MapContainer, Polyline=MapContainer, Popup=MapContainer, Tooltip=MapContainer;
      export const TileLayer=()=>null, useMap=()=>({}), useMapEvents=()=>({});`;
  },
}]});
const generated = await bundle.generate({format:'esm'});
await bundle.close();
const target = path.join(root,'.runtime/frontend-render-check.mjs');
await mkdir(path.dirname(target),{recursive:true});
await writeFile(target,generated.output[0].code);
const {FleetPage,RoutePlanner,LiveCameraPanel,routeAlerts,alertSignature,GovernmentLayout,GovernmentRoute} = await import(pathToFileURL(target));
const render = (Component,props={}) => renderToStaticMarkup(React.createElement(MemoryRouter,null,React.createElement(Component,props)));
assert.match(render(FleetPage),/Connect your first vehicle/);
assert.match(render(RoutePlanner),/Loading incident alerts/);
assert.match(render(LiveCameraPanel,{cameras:[],onRegister:()=>{}}),/No camera connected/);
assert.match(render(LiveCameraPanel,{cameras:[{id:1,bus_id:1,camera_code:'FRONT',camera_type:'front',status:'active'}],onRegister:()=>{}}),/Connect camera/);
// Neither government entry may render its contents before server verification.
assert.match(render(GovernmentLayout),/Checking government session/);
const guarded=render(GovernmentRoute,{children:React.createElement('div',null,'private-government-content')});
assert.match(guarded,/Checking government session/);
assert.doesNotMatch(guarded,/private-government-content/);
const rows=[{id:1,latitude:13,longitude:77.6,alert_type:'accident',is_demo:true},{id:2,latitude:13.1,longitude:77.5,alert_type:'waterlogging'},{id:3,latitude:null,longitude:null}];
assert.equal(routeAlerts(rows).length,2); // Alerts are visible before any route exists.
const along=[{...rows[0],distance_from_route_m:20}];
assert.equal(routeAlerts(rows,along,along,false).length,1);
assert.equal(routeAlerts(rows,along,along)[0].on_route,true);
assert.equal(routeAlerts(rows.slice(1),along,along)[0].id,2); // Resolved reports must not reappear from a cached route.
assert.equal(alertSignature(rows),alertSignature([...rows].reverse()));
assert.notEqual(alertSignature(rows),alertSignature(rows.slice(1)));
console.log('Passed: initial fleet/planner renders, government access gates, camera prompts, and live alert visibility.');
