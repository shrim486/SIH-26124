import { IncidentEvidence } from '../../../shared/AnalysisResults';

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const getToken = () => sessionStorage.getItem('government_token');

export default function IssueEvidence({ incidentId }) {
  return <IncidentEvidence key={incidentId} apiBase={apiBase} getToken={getToken} incidentId={incidentId} compact />;
}
