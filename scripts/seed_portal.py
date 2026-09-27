"""Restore shared footage map records into an empty database, preserving existing installations."""
import argparse
from datetime import timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def seed(root):
    os.chdir(root / 'backend')
    sys.path.insert(0, str(root / 'backend'))
    from app import models  # Register every table before creating a fresh database.
    from app.db.database import Base, engine, SessionLocal, ensure_sqlite_schema_compatibility
    from app.models.event import Event
    from app.models.analysis_incident import AnalysisIncident
    from app.api.routes.analysis_results import DetectionPublication, resolve_run, evidence_source
    from app.services.analysis_evidence import MODEL_TYPES
    from app.services.helmet_plates import helmet_plate_evidence
    from app.services.alert_service import records_payload, ensure_event_alert

    source = root / '.runtime/portal-seed.json'
    if not source.is_file():
        raise ValueError('Restore the portal asset bundle first: python scripts/fetch_shared_assets.py')
    payload = json.loads(source.read_text(encoding='utf-8'))
    if payload.get('schema') != 1:
        raise ValueError('Unsupported incident seed format')
    Base.metadata.create_all(engine)
    ensure_sqlite_schema_compatibility()
    with SessionLocal() as session:
        if session.query(Event).first():
            print('Existing incident database preserved; no records added or changed.')
            return
        prepared = []
        for row in payload['incidents']:
            row = dict(row)
            run = row.pop('run')
            if Path(run).name != run or run in {'.', '..'}:
                raise ValueError('Invalid seed run')
            run_id = hashlib.sha256(run.encode()).hexdigest()[:24]
            item, folder = resolve_run(run_id)
            publication = DetectionPublication(**row)
            segment = next((s for s in item['detection_segments'] if s['id'] == publication.segment_id), None)
            if segment is None:
                raise ValueError(f'Missing detection segment in {run}')
            if not item['incident_frames'].get(publication.segment_id):
                raise ValueError(f'Missing saved evidence images in {run}')
            # Restore the saved evidence without re-encoding images or rewriting indexes.
            details = dict(source='video_analysis', analysis_run_id=run_id,
                           evidence_source_key=evidence_source(item, folder), segment_id=publication.segment_id,
                           location_name=publication.location_name, description=publication.description,
                           evidence_available=True, is_demo=publication.demo,
                           location_source='simulated' if publication.demo else 'government_supplied',
                           time_source='simulated' if publication.demo else 'government_supplied',
                           method=MODEL_TYPES[segment['event_type']]['method'],
                           detected_labels=segment.get('detected_labels', []))
            if segment['event_type'] == 'helmet':
                details['helmet_plate_matches'] = helmet_plate_evidence(folder, segment)
            event = Event(event_type=segment['event_type'], confidence=segment['confidence'],
                          latitude=publication.latitude, longitude=publication.longitude,
                          timestamp=publication.occurred_at.astimezone(timezone.utc).replace(tzinfo=None),
                          severity='medium', status='demo' if publication.demo else 'new',
                          event_metadata=json.dumps(details))
            prepared.append((run_id, publication.segment_id, event))
        try:
            for run_id, segment_id, event in prepared:
                session.add(event)
                session.flush()
                session.add(AnalysisIncident(source_key=f'{run_id}:{segment_id}', event_id=event.id,
                                             run_id=run_id, segment_id=segment_id))
                ensure_event_alert(session, event)
            session.commit()
        except Exception:
            session.rollback()
            raise
        records = records_payload(session)
        print(f'Restored {records["total"]} alerts, {records["mapped"]} map positions, {records["with_evidence"]} evidence links.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    seed(args.root.resolve())


if __name__ == '__main__':
    main()
