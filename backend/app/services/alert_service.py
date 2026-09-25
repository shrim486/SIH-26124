from typing import Any, Dict, List


class AlertService:
    """Service for alert generation and tracking."""

    def __init__(self) -> None:
        self.alerts: List[Dict[str, Any]] = []

    def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        alert = {**alert_data}
        alert["id"] = len(self.alerts) + 1
        self.alerts.append(alert)
        return alert

    def get_alerts(self) -> List[Dict[str, Any]]:
        return list(self.alerts)
