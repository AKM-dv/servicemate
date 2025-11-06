import { useQuery } from "@tanstack/react-query";
import apiClient from "../services/apiClient.js";

const DashboardPage = () => {
  const formatCurrency = (value) => `INR ${Number(value || 0).toLocaleString("en-IN")}`;
  const { data, isLoading, error } = useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: () => apiClient.get("/analytics/summary").then((res) => res.data),
  });

  if (isLoading) {
    return <div>Loading analytics...</div>;
  }

  if (error) {
    return <div>Unable to load analytics.</div>;
  }

  const leadCounts = data?.lead_counts ?? [];
  const conversions = data?.conversions_by_plan ?? [];
  const revenue = data?.monthly_revenue ?? [];
  const overdue = data?.overdue?.overdue_count ?? 0;

  return (
    <div className="dashboard">
      <div className="card-grid">
        {leadCounts.map((item) => (
          <div key={item.status} className="card">
            <div className="card-title">{item.status}</div>
            <div className="card-value">{item.total}</div>
          </div>
        ))}
        <div className="card">
          <div className="card-title">Overdue Payments</div>
          <div className="card-value">{overdue}</div>
        </div>
      </div>

      <div className="split-layout" style={{ marginTop: 32 }}>
        <div className="card">
          <div className="card-title">Conversions by Plan</div>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {conversions.map((item) => (
              <li key={item.plan_name} style={{ marginBottom: 8 }}>
                {item.plan_name}: {item.total}
              </li>
            ))}
            {conversions.length === 0 && <li>No conversions yet.</li>}
          </ul>
        </div>
        <div className="card">
          <div className="card-title">Monthly Revenue</div>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {revenue.map((item) => (
              <li key={item.month} style={{ marginBottom: 8 }}>
                {item.month}: {formatCurrency(item.total)}
              </li>
            ))}
            {revenue.length === 0 && <li>No revenue recorded yet.</li>}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;

