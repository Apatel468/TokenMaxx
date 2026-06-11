/**
 * Admin API — employee usage metrics (admin role only).
 */
import { authFetch } from "./http.js";

/** GET /admin/employee-usage — per-user cost and model breakdown */
export function fetchEmployeeUsage() {
  return authFetch("/admin/employee-usage");
}
