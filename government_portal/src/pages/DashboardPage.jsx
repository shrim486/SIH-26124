import Overview from '../../../shared/Overview';
import { governmentApi } from '../api/governmentApi';
export default function DashboardPage() {
  return <div className="page-shell"><Overview government loadRecords={governmentApi.getRecords} loadFleet={governmentApi.getFleet}/></div>;
}
