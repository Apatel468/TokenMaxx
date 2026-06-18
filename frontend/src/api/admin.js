/**
 * Admin API — employee usage and per-user metrics (admin role only).
 */
import { authFetch } from "./http.js";

/** GET /admin/employee-usage — per-user cost and model breakdown */
export function fetchEmployeeUsage() {
  return authFetch("/admin/employee-usage");
}

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

/** GET /admin/user-metrics — detailed per-user usage metrics */
export function fetchAdminUserMetrics({
  startDate,
  endDate,
  userId,
  granularity = "daily",
} = {}) {
  return authFetch(
    `/admin/user-metrics${buildQuery({
      start_date: startDate,
      end_date: endDate,
      user_id: userId,
      granularity,
    })}`
  );
}
