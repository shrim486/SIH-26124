from collections import OrderedDict
from threading import Lock
from time import monotonic

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core.config import settings

router = APIRouter()

_tile_cache = OrderedDict()
_tile_cache_lock = Lock()
_TILE_CACHE_SECONDS = 45
_TILE_CACHE_LIMIT = 768


def _traffic_tile(kind: str, z: int, x: int, y: int) -> Response:
    if not 0 <= z <= 22 or not 0 <= x < 2**z or not 0 <= y < 2**z:
        raise HTTPException(404, 'Traffic tile is outside the supported map grid.')
    api_key = settings.TOMTOM_API_KEY.strip()
    if not api_key:
        raise HTTPException(503, 'Live traffic needs TOMTOM_API_KEY in backend/.env.')

    cache_key = (kind, z, x, y)
    now = monotonic()
    with _tile_cache_lock:
        cached = _tile_cache.get(cache_key)
        if cached and cached[0] > now:
            _tile_cache.move_to_end(cache_key)
            return Response(cached[1], media_type='image/png', headers={
                'Cache-Control': f'public, max-age={_TILE_CACHE_SECONDS}',
                'X-Content-Type-Options': 'nosniff',
            })
        if cached:
            del _tile_cache[cache_key]

    if kind == 'flow':
        url = f'https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{z}/{x}/{y}.png'
    else:
        url = f'https://api.tomtom.com/traffic/map/4/tile/incidents/s0/{z}/{x}/{y}.png'
    try:
        upstream = httpx.get(url, params={'key': api_key, 't': '-1', 'tileSize': 256},
            timeout=12, headers={'Accept': 'image/png, application/json', 'User-Agent': settings.MAP_USER_AGENT})
    except httpx.HTTPError as exc:
        raise HTTPException(502, 'TomTom traffic tiles could not be reached. Retry in a moment.') from exc

    if upstream.status_code in (401, 403):
        raise HTTPException(503, 'TomTom rejected the traffic tile request. Enable Traffic API access for this key.')
    if upstream.status_code == 429:
        raise HTTPException(503, 'TomTom traffic tile limit reached. Retry shortly.')
    if upstream.status_code != 200 or not upstream.headers.get('content-type', '').lower().startswith('image/png'):
        raise HTTPException(502, 'TomTom did not return a traffic map tile.')

    image = upstream.content
    with _tile_cache_lock:
        _tile_cache[cache_key] = (monotonic() + _TILE_CACHE_SECONDS, image)
        _tile_cache.move_to_end(cache_key)
        while len(_tile_cache) > _TILE_CACHE_LIMIT:
            _tile_cache.popitem(last=False)
    return Response(image, media_type='image/png', headers={
        'Cache-Control': f'public, max-age={_TILE_CACHE_SECONDS}',
        'X-Content-Type-Options': 'nosniff',
    })


@router.get("/test")
def traffic_test():
    return {"message": "Traffic API working"}


@router.get('/traffic/tiles/flow/{z}/{x}/{y}.png', response_class=Response)
def traffic_flow_tile(z: int, x: int, y: int):
    return _traffic_tile('flow', z, x, y)


@router.get('/traffic/tiles/incidents/{z}/{x}/{y}.png', response_class=Response)
def traffic_incident_tile(z: int, x: int, y: int):
    return _traffic_tile('incidents', z, x, y)
