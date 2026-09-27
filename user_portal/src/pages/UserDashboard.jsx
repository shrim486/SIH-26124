import Overview from '../../../shared/Overview';
import { userApi } from '../api/userApi';
export default function UserDashboard() {
  return <Overview loadRecords={userApi.getRecords}/>;
}
