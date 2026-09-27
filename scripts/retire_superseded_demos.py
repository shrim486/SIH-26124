"""Retire only the replaced rider demos and duplicate waterlogging map examples.

Defaults to a preview. --apply backs up the exact rows before a DB transaction.
Raw videos and completed model outputs are retained. Real reports are excluded.
Run after publish_demo_detections.py so replacement evidence is already linked.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_id(name):
    return hashlib.sha256(name.encode()).hexdigest()[:24]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'backend'))
    os.chdir(ROOT / 'backend')
    from app.db.database import SessionLocal
    from app.models.event import Event
    from app.models.analysis_incident import AnalysisIncident
    from app.models.alert_event import AlertEvent
    from app.models.alert import Alert
    from app.services.analysis_evidence import detection_segments

    replacement = run_id('demo_slow_riders')
    segments = {s['id']: s for s in detection_segments(ROOT / 'edge_ai/outputs/demo_slow_riders')}
    superseded = {
        (run_id('demo_motorcycles'), 'helmet'),
        (run_id('demo_motorcycles'), 'number_plate'),
        (run_id('demo_triple_riders'), 'helmet'),
        (run_id('extended_suite_reviewed'), 'waterlogging'),
    }
    with SessionLocal.begin() as db:
        rows = db.query(AnalysisIncident, Event).join(Event, Event.id == AnalysisIncident.event_id).all()
        new_links = [link for link, event in rows if link.run_id == replacement]
        kinds = {segments[link.segment_id]['event_type'] for link in new_links if link.segment_id in segments}
        labels = {label for link in new_links if link.segment_id in segments
                  for label in segments[link.segment_id].get('detected_labels', [])}
        if not {'helmet', 'number_plate'} <= kinds or not {'with_helmet', 'without_helmet'} <= labels:
            raise RuntimeError('Publish the new plate and BOTH helmet-class evidence segments before retiring old demos.')
        if not any(link.run_id == run_id('demo_waterlogging') and event.event_type == 'waterlogging' for link, event in rows):
            raise RuntimeError('The dedicated waterlogging map example must already be published.')
        selected = [(link, event) for link, event in rows
                    if (link.run_id, event.event_type) in superseded
                    and event.status == 'demo'
                    and json.loads(event.event_metadata or '{}').get('is_demo') is True]
        print('Superseded demo event IDs:', [event.id for _, event in selected])
        if not args.apply or not selected:
            return
        def record(model):
            return {column.name: getattr(model, column.name) for column in model.__table__.columns}
        backup = ROOT / '.runtime' / ('retired-demos-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        backup.parent.mkdir(exist_ok=True)
        alert_links = db.query(AlertEvent).filter(AlertEvent.event_id.in_([event.id for _, event in selected])).all()
        alerts = [db.get(Alert, link.alert_id) for link in alert_links]
        backup.write_text(json.dumps({'events': [{'event': record(event), 'analysis_incident': record(link)}
                                      for link, event in selected], 'alert_links': [record(link) for link in alert_links],
                                      'alerts': [record(alert) for alert in alerts if alert]}, indent=2, default=str), encoding='utf-8')
        for link in alert_links:
            db.delete(link)
        for link, event in selected:
            db.delete(link)
        db.flush()
        for alert in alerts:
            if alert:
                db.delete(alert)
        for _, event in selected:
            db.delete(event)
        print('Backed up retired rows to', backup)


if __name__ == '__main__':
    main()
