import { TileLayer } from 'react-leaflet';

export function MapBaseLayer() {
  return <TileLayer
    url="https://services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
    maxZoom={19}
    attribution='Topographic map: Sources &copy; Esri, HERE, Garmin, Intermap, increment P Corp., GEBCO, USGS, FAO, NPS, NRCan, GeoBase, IGN, Kadaster NL, Ordnance Survey, Esri Japan, METI, OpenStreetMap contributors, and the GIS User Community'
  />;
}
