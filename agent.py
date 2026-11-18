# agent.py
from tools import FleetTools

class FleetCopilotAgent:
    def __init__(self, tools: FleetTools):
        self.tools = tools
        
    def _detect_company_context(self, user_query: str) -> str:
        query_lower = user_query.lower()
        if 'acme' in query_lower:
            return 'acme-001'
        elif 'globex' in query_lower:
            return 'globex-002'
        elif 'initech' in query_lower:
            return 'initech-003'
        return None

    def execute_agent_loop(self, user_query: str, admin_company_id: str = None) -> dict:
        detected_company = self._detect_company_context(user_query)
        
        if admin_company_id and detected_company and detected_company != admin_company_id:
            return {
                "response": f"Access Denied: Your account is isolated to {admin_company_id}. You cannot access data for {detected_company}.",
                "evidence_cited": [],
                "proposed_actions": []
            }
            
        company_id = detected_company or admin_company_id
        if not company_id:
            return {
                "response": "Could not identify company context. Please specify Acme, Globex, or Initech.",
                "evidence_cited": [],
                "proposed_actions": []
            }

        query_lower = user_query.lower()
        response_text = ""
        evidence_cited = []
        proposed_actions = []

        # 1. Disk Space Query Logic
        if "disk" in query_lower or "storage" in query_lower:
            snapshots = self.tools.query_fleet_telemetry(company_id)
            low_disk = [s for s in snapshots if s['disk_free_gb'] < 20.0]
            
            if low_disk:
                response_text = f"Found {len(low_disk)} device(s) at {company_id} with critically low disk space (<20GB free):\n"
                for dev in low_disk:
                    dev_id = dev['device_id']
                    free_gb = dev['disk_free_gb']
                    total_gb = dev['disk_total_gb']
                    emp_id = dev['employee_id']
                    
                    response_text += f"- **Device {dev_id}** (Assigned to {emp_id}): {round(free_gb, 2)}GB free of {round(total_gb, 2)}GB total.\n"
                    evidence_cited.append({
                        "device_id": dev_id,
                        "metric": f"disk_free_gb: {round(free_gb, 2)}GB",
                        "timestamp": dev['timestamp']
                    })
                    proposed_actions.append({
                        "tool": "create_upgrade_order",
                        "args": {
                            "company_id": company_id,
                            "device_id": dev_id,
                            "component": "disk",
                            "spec": f"{int(total_gb * 2)}GB SSD Upgrade"
                        },
                        "justification": f"Device {dev_id} has only {round(free_gb, 2)}GB free storage left (<20GB safety threshold)."
                    })
            else:
                response_text = f"All active devices at {company_id} have sufficient disk space (>20GB free)."

        # 2. Compliance Query Logic
        elif "compliance" in query_lower or "failing" in query_lower or "security" in query_lower:
            snapshots = self.tools.query_fleet_telemetry(company_id)
            failing = [s for s in snapshots if s['high_severity_failure']]
            
            if failing:
                response_text = f"Found {len(failing)} device(s) at {company_id} failing compliance checks:\n"
                for dev in failing:
                    dev_id = dev['device_id']
                    check_id = dev['compliance_results.check_id']
                    severity = dev['compliance_results.severity']
                    emp_id = dev['employee_id']
                    
                    response_text += f"- **Device {dev_id}** (Assigned to {emp_id}): Failing check '{check_id}' (Severity: {severity}).\n"
                    evidence_cited.append({
                        "device_id": dev_id,
                        "metric": f"check_failing: {check_id}, severity: {severity}",
                        "timestamp": dev['timestamp']
                    })
                    proposed_actions.append({
                        "tool": "open_remediation_ticket",
                        "args": {
                            "company_id": company_id,
                            "device_id": dev_id,
                            "check_id": check_id,
                            "note": f"Remediation required for compliance check failure: {check_id}."
                        },
                        "justification": f"Device {dev_id} failed compliance check: {check_id}."
                    })
                    proposed_actions.append({
                        "tool": "notify_employee",
                        "args": {
                            "company_id": company_id,
                            "employee_id": emp_id,
                            "message": f"Please remediate the compliance check failure '{check_id}' on device {dev_id}."
                        },
                        "justification": f"Notify employee {emp_id} immediately to prompt self-remediation."
                    })
            else:
                response_text = f"All devices at {company_id} are fully compliant with security policies."

        # 3. Battery Degraded Query Logic
        elif "battery" in query_lower or "end-of-life" in query_lower or "replace" in query_lower:
            snapshots = self.tools.query_fleet_telemetry(company_id)
            bad_battery = [s for s in snapshots if s['battery_condition'] == 'Service Recommended']
            
            if bad_battery:
                response_text = f"Found {len(bad_battery)} device(s) at {company_id} with degrading battery health (Service Recommended):\n"
                for dev in bad_battery:
                    dev_id = dev['device_id']
                    battery_pct = dev['battery_health_pct']
                    emp_id = dev['employee_id']
                    
                    response_text += f"- **Device {dev_id}** (Assigned to {emp_id}): Battery condition is Service Recommended. Current capacity: {battery_pct}%.\n"
                    evidence_cited.append({
                        "device_id": dev_id,
                        "metric": f"battery_condition: Service Recommended, percentage: {battery_pct}%",
                        "timestamp": dev['timestamp']
                    })
                    proposed_actions.append({
                        "tool": "flag_device_for_replacement",
                        "args": {
                            "company_id": company_id,
                            "device_id": dev_id,
                            "reason": f"Battery condition degraded (Condition: Service Recommended)."
                        },
                        "justification": f"Device {dev_id}'s battery status is flagged as 'Service Recommended'."
                    })
            else:
                response_text = f"All devices at {company_id} have healthy batteries (no Service Recommended warnings)."

        # 4. Consistently Constrained RAM (Time-Series Aggregator)
        elif "ram" in query_lower or "memory" in query_lower or "constrained" in query_lower:
            devices = self.tools.list_devices(company_id)
            constrained_devices = []
            
            for d in devices:
                dev_id = d['device_id']
                history = self.tools.get_device_history(company_id, dev_id)
                
                # Perform arithmetic rolling average calculation in vanilla Python
                total_ram_used = sum(h['ram_used_gb'] for h in history)
                avg_ram_used = total_ram_used / len(history)
                ram_total = history[0]['ram_total_gb']
                pct = avg_ram_used / ram_total
                
                if pct > 0.85:
                    constrained_devices.append({
                        'device_id': dev_id,
                        'avg_ram_used': avg_ram_used,
                        'ram_total': ram_total,
                        'employee_id': d['employee_id'],
                        'pct_desc': f"{round(pct*100, 1)}%",
                        'timestamp': history[-1]['collected_at']
                    })
            
            if constrained_devices:
                response_text = f"Found {len(constrained_devices)} device(s) at {company_id} consistently constrained by RAM (>85% average usage):\n"
                for dev in constrained_devices:
                    dev_id = dev['device_id']
                    pct_desc = dev['pct_desc']
                    response_text += f"- **Device {dev_id}** (Assigned to {dev['employee_id']}): Average RAM usage is {round(dev['avg_ram_used'], 1)}GB of {round(dev['ram_total'], 1)}GB ({pct_desc}).\n"
                    evidence_cited.append({
                        "device_id": dev_id,
                        "metric": f"avg_ram_utilization: {pct_desc}",
                        "timestamp": dev['timestamp']
                    })
                    proposed_actions.append({
                        "tool": "create_upgrade_order",
                        "args": {
                            "company_id": company_id,
                            "device_id": dev_id,
                            "component": "RAM",
                            "spec": f"Upgrade to {int(dev['ram_total'] * 2)}GB RAM"
                        },
                        "justification": f"Device {dev_id} is consistently bottlenecked on RAM with average usage at {pct_desc}."
                    })
            else:
                response_text = f"No devices at {company_id} show signs of constant RAM constraint."

        # 5. Default Dashboard Summary Layout
        else:
            snapshots = self.tools.query_fleet_telemetry(company_id)
            failing = [s for s in snapshots if s['high_severity_failure']]
            low_storage = [s for s in snapshots if s['disk_free_gb'] < 20.0]
            bad_batt = [s for s in snapshots if s['battery_condition'] == 'Service Recommended']
            
            response_text = (
                f"### Fleet Summary for {company_id}\n"
                f"- **Total Managed Devices**: {len(snapshots)}\n"
                f"- **Security Non-Compliant**: {len(failing)} device(s)\n"
                f"- **Critically Low Storage (<20GB)**: {len(low_storage)} device(s)\n"
                f"- **Degraded Batteries (Service Recommended)**: {len(bad_batt)} device(s)\n"
                f"How would you like to drill down into any of these issues?"
            )
            
        return {
            "response": response_text,
            "evidence_cited": evidence_cited,
            "proposed_actions": proposed_actions
        }
