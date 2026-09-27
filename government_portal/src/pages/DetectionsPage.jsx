import SafetyAlerts from '../../../shared/SafetyAlerts';
import { governmentApi } from '../api/governmentApi';
import IssueEvidence from '../components/IssueEvidence';
import IssuesPage from './IssuesPage';
import { useSearchParams } from 'react-router-dom';
const renderEvidence=alert=><IssueEvidence incidentId={alert.event_id}/>;
export default function DetectionsPage(){const [params]=useSearchParams();if(params.has('issue')||params.has('bus'))return <IssuesPage/>;return <div className="page-shell"><SafetyAlerts government title="Detected issues" loadRecords={governmentApi.getRecords} updateAlert={governmentApi.updateAlertStatus} updateIssue={governmentApi.updateIssueStatus} renderEvidence={renderEvidence}/></div>;}
