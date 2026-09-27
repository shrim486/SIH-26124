import { userApi } from '../api/userApi';
import SafetyAlerts from '../../../shared/SafetyAlerts';

export default function Alerts() {
  return <div className="user-page"><SafetyAlerts loadRecords={userApi.getRecords} /></div>;
}
