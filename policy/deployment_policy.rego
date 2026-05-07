package devsecops.policy

import rego.v1

default allow := false

critical_count := object.get(input, "critical_count", 0)
high_count := object.get(input, "high_count", 0)
medium_count := object.get(input, "medium_count", 0)
secrets_count := object.get(input, "secrets_count", 0)

allow if {
  critical_count == 0
  high_count == 0
  secrets_count == 0
}

deny contains msg if {
  critical_count > 0
  msg := sprintf("Deployment blocked: %v critical vulnerabilities found", [critical_count])
}

deny contains msg if {
  high_count > 0
  msg := sprintf("Deployment blocked: %v high vulnerabilities found", [high_count])
}

deny contains msg if {
  secrets_count > 0
  msg := sprintf("Deployment blocked: %v secrets found", [secrets_count])
}
