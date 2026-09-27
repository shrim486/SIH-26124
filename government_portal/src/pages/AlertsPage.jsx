import { governmentApi } from '../api/governmentApi';
import SafetyAlerts from '../../../shared/SafetyAlerts';
import IssueEvidence from '../components/IssueEvidence';

const renderEvidence = alert => <IssueEvidence incidentId={alert.event_id} />;

export default function AlertsPage() {
  return <div className="page-shell"><SafetyAlerts government loadRecords={governmentApi.getRecords} updateAlert={governmentApi.updateAlertStatus} updateIssue={governmentApi.updateIssueStatus} renderEvidence={renderEvidence} /></div>;
}
