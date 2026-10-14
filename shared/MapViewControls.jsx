import { useEffect } from 'react';
import L from 'leaflet';
import { ScaleControl, useMap, ZoomControl } from 'react-leaflet';

const locationIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/></svg>';
const fullscreenIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/></svg>';
const exitFullscreenIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3v5H3m13-5v5h5M3 16h5v5m13-5h-5v5"/></svg>';

function FloatingLocationAndFullscreen() {
  const map = useMap();

  useEffect(() => {
    let marker = null;
    let accuracyRing = null;
    let locationButton = null;
    let fullscreenButton = null;
    const fullscreenShell = map.getContainer().parentElement;
    fullscreenShell?.classList.add('map-fullscreen-shell');

    const control = L.control({ position: 'bottomright' });
    control.onAdd = () => {
      const group = L.DomUtil.create('div', 'map-view-tools');
      L.DomEvent.disableClickPropagation(group);
      L.DomEvent.disableScrollPropagation(group);

      locationButton = L.DomUtil.create('button', 'map-view-tool', group);
      locationButton.type = 'button';
      locationButton.innerHTML = locationIcon;
      locationButton.title = 'Show my location';
      locationButton.setAttribute('aria-label', 'Show my location');
      L.DomEvent.on(locationButton, 'click', () => {
        if (!navigator.geolocation) {
          locationButton.title = 'Location is not available in this browser';
          locationButton.classList.add('has-error');
          return;
        }
        locationButton.classList.remove('has-error');
        locationButton.title = 'Finding your location…';
        navigator.geolocation.getCurrentPosition(position => {
          const { latitude, longitude, accuracy } = position.coords;
          const point = [latitude, longitude];
          if (marker) map.removeLayer(marker);
          if (accuracyRing) map.removeLayer(accuracyRing);
          accuracyRing = L.circle(point, {
            radius: Math.min(accuracy || 0, 1000),
            color: '#4285f4',
            weight: 1,
            fillColor: '#4285f4',
            fillOpacity: 0.12,
          }).addTo(map);
          marker = L.circleMarker(point, {
            radius: 8,
            color: '#fff',
            weight: 3,
            fillColor: '#4285f4',
            fillOpacity: 1,
          }).addTo(map);
          map.flyTo(point, Math.max(map.getZoom(), 15), { duration: 0.7 });
          locationButton.title = 'Show my location';
        }, () => {
          locationButton.title = 'Could not get your location. Check browser location permission.';
          locationButton.classList.add('has-error');
        }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 });
      });

      fullscreenButton = L.DomUtil.create('button', 'map-view-tool', group);
      fullscreenButton.type = 'button';
      fullscreenButton.innerHTML = fullscreenIcon;
      fullscreenButton.title = 'Full screen map';
      fullscreenButton.setAttribute('aria-label', 'Full screen map');
      L.DomEvent.on(fullscreenButton, 'click', () => {
        if (document.fullscreenElement === fullscreenShell) {
          document.exitFullscreen?.();
        } else {
          const request = fullscreenShell?.requestFullscreen?.();
          request?.catch?.(() => {
            fullscreenButton.title = 'Full screen is unavailable in this browser';
          });
        }
      });
      return group;
    };

    const syncFullscreenButton = () => {
      if (!fullscreenButton) return;
      const active = document.fullscreenElement === fullscreenShell;
      fullscreenButton.innerHTML = active ? exitFullscreenIcon : fullscreenIcon;
      fullscreenButton.title = active ? 'Exit full screen' : 'Full screen map';
      fullscreenButton.setAttribute('aria-label', fullscreenButton.title);
      window.setTimeout(() => map.invalidateSize(), 150);
    };

    document.addEventListener('fullscreenchange', syncFullscreenButton);
    control.addTo(map);
    return () => {
      document.removeEventListener('fullscreenchange', syncFullscreenButton);
      map.removeControl(control);
      if (marker) map.removeLayer(marker);
      if (accuracyRing) map.removeLayer(accuracyRing);
      fullscreenShell?.classList.remove('map-fullscreen-shell');
    };
  }, [map]);

  return <>
    <ZoomControl position="bottomright"/>
    <ScaleControl position="bottomleft" metric imperial={false}/>
  </>;
}

export default FloatingLocationAndFullscreen;
