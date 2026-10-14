import SafetyAlerts from '../../../shared/SafetyAlerts';
import { userApi } from '../api/userApi';
export default function LiveMap(){return <SafetyAlerts title="Incident map" subtitle="Explore reported road issues and their locations." loadRecords={userApi.getRecords}/>;}
