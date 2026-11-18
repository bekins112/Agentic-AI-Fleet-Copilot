# tools.py
import csv
import json
from datetime import datetime

class FleetTools:
    def __init__(self, data_path='data.csv'):
        self.data_path = data_path
        self.audit_logs = []

    def _read_data(self):
        """Reads rows as dictionaries from the CSV file."""
        with open(self.data_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _log_audit(self, action: str, company_id: str, details: dict, status: str):
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': action,
            'company_id': company_id,
            'details': details,
            'status': status
        }
        self.audit_logs.append(log_entry)
        try:
            with open('audit_log.json', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception:
            pass

    def _verify_device_tenant(self, company_id: str, device_id: str) -> bool:
        """Enforces tenant isolation by verifying device ownership."""
        for row in self._read_data():
            if row['device_id'] == device_id:
                return row['company_id'] == company_id
        return False

    def _verify_employee_tenant(self, company_id: str, employee_id: str) -> bool:
        """Enforces tenant isolation by verifying employee ownership."""
        for row in self._read_data():
            if row['employee_id'] == employee_id:
                return row['company_id'] == company_id
        return False

    def list_devices(self, company_id: str):
        """Get all unique devices for a specific company."""
        seen_devices = set()
        devices = []
        for row in self._read_data():
            if row['company_id'] == company_id and row['device_id'] not in seen_devices:
                seen_devices.add(row['device_id'])
                
                # Calculate RAM and Storage totals in GB
                total_memory_bytes = float(row.get('memory.total_memory_bytes') or 0)
                size_bytes = float(row.get('disk_volumes.size_bytes') or 0)
                
                devices.append({
                    'device_id': row['device_id'],
                    'employee_id': row['employee_id'],
                    'company_id': row['company_id'],
                    'model': row['device_identity.model_name'],
                    'os_name': row['os.platform'],
                    'os_version': row['os.product_version'],
                    'ram_total_gb': total_memory_bytes / (1024**3),
                    'disk_total_gb': size_bytes / (1024**3)
                })
        return devices

    def query_fleet_telemetry(self, company_id: str):
        """Get latest telemetry snapshots for a specific company's devices."""
        device_snapshots = {}
        for row in self._read_data():
            if row['company_id'] == company_id:
                dev_id = row['device_id']
                collected_at = row['collected_at']
                
                # Maintain the latest snapshot based on datetime string comparison
                if dev_id not in device_snapshots or collected_at > device_snapshots[dev_id]['collected_at']:
                    device_snapshots[dev_id] = row

        latest_snapshots = []
        for row in device_snapshots.values():
            available_bytes = float(row.get('disk_volumes.available_bytes') or 0)
            size_bytes = float(row.get('disk_volumes.size_bytes') or 0)
            total_memory_bytes = float(row.get('memory.total_memory_bytes') or 0)
            used_memory_bytes = float(row.get('memory.used_memory_bytes') or 0)
            battery_pct = float(row.get('battery.percentage') or 0) if row.get('battery.percentage') else None

            latest_snapshots.append({
                'device_id': row['device_id'],
                'employee_id': row['employee_id'],
                'company_id': row['company_id'],
                'collected_at': row['collected_at'],
                'timestamp': row['collected_at'],
                'disk_free_gb': available_bytes / (1024**3),
                'disk_total_gb': size_bytes / (1024**3),
                'ram_total_gb': total_memory_bytes / (1024**3),
                'ram_used_gb': used_memory_bytes / (1024**3),
                'battery_health_pct': battery_pct,
                'battery_condition': row.get('battery.condition'),
                'firewall_enabled': True,
                'disk_encrypted': row.get('disk_volumes.encrypted') == 'True',
                'compliance_results.status': row.get('compliance_results.status'),
                'compliance_results.check_id': row.get('compliance_results.check_id'),
                'compliance_results.severity': row.get('compliance_results.severity'),
                'high_severity_failure': row.get('compliance_results.status') == 'fail'
            })
        return latest_snapshots

    def get_device_history(self, company_id: str, device_id: str):
        """Get full snapshot history for a specific device."""
        if not self._verify_device_tenant(company_id, device_id):
            raise PermissionError(f"Access Denied: Device {device_id} does not belong to {company_id}.")
        
        history = []
        for row in self._read_data():
            if row['device_id'] == device_id:
                available_bytes = float(row.get('disk_volumes.available_bytes') or 0)
                size_bytes = float(row.get('disk_volumes.size_bytes') or 0)
                total_memory_bytes = float(row.get('memory.total_memory_bytes') or 0)
                used_memory_bytes = float(row.get('memory.used_memory_bytes') or 0)
                
                snap = dict(row)
                snap['timestamp'] = row['collected_at']
                snap['disk_free_gb'] = available_bytes / (1024**3)
                snap['disk_total_gb'] = size_bytes / (1024**3)
                snap['ram_total_gb'] = total_memory_bytes / (1024**3)
                snap['ram_used_gb'] = used_memory_bytes / (1024**3)
                history.append(snap)
        
        # Sort history by collected_at
        history.sort(key=lambda x: x['collected_at'])
        return history

    def create_upgrade_order(self, company_id: str, device_id: str, component: str, spec: str):
        if not self._verify_device_tenant(company_id, device_id):
            self._log_audit('create_upgrade_order', company_id, {'device_id': device_id, 'component': component}, 'DENIED')
            return {"status": "error", "message": "Tenant boundary violation."}
        
        history = self.get_device_history(company_id, device_id)
        
        evidence_justified = False
        reason = ""
        
        if component.lower() == 'ram':
            avg_ram_used = sum(r['ram_used_gb'] for r in history) / len(history)
            ram_total = history[0]['ram_total_gb']
            if (avg_ram_used / ram_total) > 0.85:
                evidence_justified = True
            else:
                reason = f"Average RAM usage is {round(avg_ram_used, 1)}GB / {round(ram_total, 1)}GB ({round(avg_ram_used/ram_total*100, 1)}%), which is below threshold (>85%)."
        elif component.lower() in ['disk', 'storage']:
            min_disk_free = min(r['disk_free_gb'] for r in history)
            if min_disk_free < 20.0:
                evidence_justified = True
            else:
                reason = f"Minimum free storage is {round(min_disk_free, 1)}GB, which is above safety threshold (<20GB)."
        else:
            reason = f"Unsupported upgrade component: {component}."

        if not evidence_justified:
            self._log_audit('create_upgrade_order', company_id, {'device_id': device_id, 'component': component, 'spec': spec}, f'REJECTED - {reason}')
            return {"status": "rejected", "message": f"Upgrade rejected: {reason}"}

        self._log_audit('create_upgrade_order', company_id, {'device_id': device_id, 'component': component, 'spec': spec}, 'APPROVED')
        return {"status": "success", "message": f"Upgrade order for {component} ({spec}) on device {device_id} approved."}

    def open_remediation_ticket(self, company_id: str, device_id: str, check_id: str, note: str):
        if not self._verify_device_tenant(company_id, device_id):
            self._log_audit('open_remediation_ticket', company_id, {'device_id': device_id}, 'DENIED')
            return {"status": "error", "message": "Tenant boundary violation."}
        
        latest_snaps = self.query_fleet_telemetry(company_id)
        dev_snap = next((s for s in latest_snaps if s['device_id'] == device_id), None)
        
        if not dev_snap:
            return {"status": "error", "message": "No telemetry available."}
        
        if not dev_snap['high_severity_failure']:
            reason = "Compliance check is passing on latest records."
            self._log_audit('open_remediation_ticket', company_id, {'device_id': device_id}, f'REJECTED - {reason}')
            return {"status": "rejected", "message": reason}

        self._log_audit('open_remediation_ticket', company_id, {'device_id': device_id, 'check_id': check_id, 'note': note}, 'APPROVED')
        return {"status": "success", "message": f"Remediation ticket opened for {device_id}."}

    def flag_device_for_replacement(self, company_id: str, device_id: str, reason: str):
        if not self._verify_device_tenant(company_id, device_id):
            self._log_audit('flag_device_for_replacement', company_id, {'device_id': device_id}, 'DENIED')
            return {"status": "error", "message": "Tenant boundary violation."}
        
        history = self.get_device_history(company_id, device_id)
        latest_rec = history[-1]
        battery_condition = latest_rec.get('battery.condition')
        
        if battery_condition == 'Normal':
            rejection = "Device battery health is Normal."
            self._log_audit('flag_device_for_replacement', company_id, {'device_id': device_id}, f'REJECTED - {rejection}')
            return {"status": "rejected", "message": rejection}

        self._log_audit('flag_device_for_replacement', company_id, {'device_id': device_id, 'reason': reason}, 'APPROVED')
        return {"status": "success", "message": f"Device {device_id} flagged for replacement."}

    def notify_employee(self, company_id: str, employee_id: str, message: str):
        if not self._verify_employee_tenant(company_id, employee_id):
            self._log_audit('notify_employee', company_id, {'employee_id': employee_id}, 'DENIED')
            return {"status": "error", "message": "Tenant boundary violation."}
        
        self._log_audit('notify_employee', company_id, {'employee_id': employee_id, 'message': message}, 'SENT')
        return {"status": "success", "message": "Notification sent successfully."}
