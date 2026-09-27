import React from 'react';
import { useSearchParams } from 'react-router-dom';
import VideoAnalysis from '../../../shared/VideoAnalysis';
import { API_BASE_URL } from '../api/userApi';
const getToken = () => sessionStorage.getItem('government_token');
export default function VideoAnalysisPage() {
  const [params] = useSearchParams();
  return <VideoAnalysis apiBase={API_BASE_URL} getToken={getToken} incidentId={params.get('incident')} />;
}
