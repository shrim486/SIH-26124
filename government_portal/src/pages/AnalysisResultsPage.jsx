import { Link, useSearchParams } from 'react-router-dom';
import AnalysisResults from '../../../shared/AnalysisResults';
import EvidenceLibrary from './EvidenceLibrary';
const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const getToken = () => sessionStorage.getItem('government_token');
export default function AnalysisResultsPage() {
  const [params] = useSearchParams(),id = params.get('incident');
  if (!id) return <EvidenceLibrary />;
  return <section className="page-shell civic-ui"><header className="civic-heading"><div><span className="civic-kicker">Incident evidence</span><h1>Video & detected images</h1><p><Link to={`/detections?issue=${id}`}>Review case & map</Link> · <Link to="/ai-results">All recordings</Link></p></div></header>
    <AnalysisResults apiBase={apiBase} getToken={getToken} incidentId={id} /></section>;
}
