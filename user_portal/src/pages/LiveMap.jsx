import SafetyAlerts from '../../../shared/SafetyAlerts';
import { userApi } from '../api/userApi';
export default function LiveMap(){return <SafetyAlerts title="Incident map" loadRecords={userApi.getRecords}/>;}
