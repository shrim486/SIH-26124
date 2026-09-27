"""Create location/evidence-linked in-app alerts for already published detections.

Preview by default. --apply saves a row backup and updates the local database.
Demos remain demos, matched plate OCR is unverified, and retries preserve dismissals.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'backend'))
    os.chdir(ROOT / 'backend')
    from app.db.database import SessionLocal
    from app.models.alert import Alert
    from app.models.alert_event import AlertEvent
    from app.models.analysis_incident import AnalysisIncident
    from app.models.event import Event
    from app.api.routes.analysis_results import resolve_run
    from app.services.alert_service import metadata, event_alert_type, ensure_event_alert
    from app.services.analysis_evidence import prepare_alert_evidence
    with SessionLocal.begin() as db:
        rows = db.query(AnalysisIncident, Event).join(Event, Event.id == AnalysisIncident.event_id).all()
        prepared = []
        for link, event in rows:
            item, folder = resolve_run(link.run_id)
            segment = next(s for s in item['detection_segments'] if s['id'] == link.segment_id)
            original = event.event_metadata
            details = {**metadata(event), 'detected_labels': segment.get('detected_labels', [])}
            event.event_metadata = json.dumps(details)
            kind = event_alert_type(event)
            event.event_metadata = original
            if kind:
                prepared.append((event, folder, segment))
                print(f'Incident #{event.id}: {kind}, demo={details.get("is_demo", False)}')
        if not args.apply:
            return
        def record(model):
            return {column.name: getattr(model, column.name) for column in model.__table__.columns}
        backup = ROOT / '.runtime' / ('before-alert-sync-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        backup.parent.mkdir(exist_ok=True)
        backup.write_text(json.dumps({'events': [record(e) for e, _, _ in prepared],
                                      'alerts': [record(a) for a in db.query(Alert).all()],
                                      'links': [record(a) for a in db.query(AlertEvent).all()]}, indent=2, default=str))
        for event, folder, segment in prepared:
            details = {**metadata(event), **prepare_alert_evidence(folder, segment)}
            event.event_metadata = json.dumps(details)
            alert = ensure_event_alert(db, event)
            print(f'Linked incident #{event.id} to alert #{alert.id}')
        print('Backup:', backup.name)


if __name__ == '__main__':
    main()
