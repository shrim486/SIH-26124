import requests

class APIClient:
    def __init__(self, backend_url="http://127.0.0.1:8000/api/v1/events/ingest"):
        self.backend_url = backend_url

    def send_alert(self, alert):
        payload = {
            "event_type": alert["event_type"],
            "confidence": alert["confidence"],
            "latitude": alert["latitude"],
            "longitude": alert["longitude"],
            "timestamp": alert["timestamp"],
            "bus_id": 1,
            "camera_id": 1,
            "metadata": {
                "source": "edge_ai",
                "model": "waterlogging",
                "report_count": alert["report_count"],
                "status": alert["status"]
            },
            "severity": alert["severity"],
            "registration_number": "BUS_01"
        }

        print("Sending alert to backend...")
        print("URL:", self.backend_url)
        print("Payload:", payload)

        try:
            response = requests.post(
                self.backend_url,
                json=payload,
                timeout=10
            )

            print("HTTP Status:", response.status_code)
            response.raise_for_status()
            print("Alert sent successfully.")
            print("Backend response:", response.text)
            return True

        except requests.RequestException as error:
            print("ERROR: Could not send alert.")
            print(error)
            return False
