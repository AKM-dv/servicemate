import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "../services/apiClient.js";
import StatusBadge from "../components/StatusBadge.jsx";

const initialForm = {
  phone: "",
  name: "",
  email: "",
  address: "",
  brand_name: "",
  preferred_plan_id: "",
};

const LeadsPage = () => {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(initialForm);
  const [filters, setFilters] = useState({
    tab: "",
    search: "",
    status: "",
    created_from: "",
    created_to: "",
  });

  const setStatusFilter = (status) => {
    setFilters((prev) => ({
      ...prev,
      tab: status,
      status,
    }));
  };

  const clearFilters = () =>
    setFilters({ tab: "", search: "", status: "", created_from: "", created_to: "" });

  const statusTabs = [
    { key: "", label: "All" },
    { key: "New", label: "New" },
    { key: "In Progress", label: "In Progress" },
    { key: "Converted", label: "Converted" },
    { key: "Lost", label: "Lost" },
    { key: "Custom", label: "Custom" },
  ];

  const { data: plans } = useQuery({
    queryKey: ["plans"],
    queryFn: () => apiClient.get("/plans").then((res) => res.data),
  });

  const { data: leads } = useQuery({
    queryKey: ["leads", filters],
    queryFn: () => {
      const params = {};
      if (filters.search) params.search = filters.search;
      if (filters.status) params.status = filters.status;
      if (filters.created_from) params.created_from = filters.created_from;
      if (filters.created_to) params.created_to = filters.created_to;
      return apiClient.get("/leads", { params }).then((res) => res.data);
    },
  });

  const createLead = useMutation({
    mutationFn: (payload) => apiClient.post("/leads", payload).then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setForm(initialForm);
    },
  });

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const payload = {
      phone: form.phone.trim(),
      name: form.name.trim() || null,
      email: form.email.trim() || null,
      address: form.address.trim() || null,
      brand_name: form.brand_name.trim() || null,
      preferred_plan_id: form.preferred_plan_id || null,
    };
    createLead.mutate(payload);
  };

  return (
    <div className="leads-page">
      <div className="status-tabs">
        {statusTabs.map((tab) => (
          <button
            key={tab.key || "all"}
            type="button"
            className={`status-tab${filters.tab === tab.key ? " status-tab-active" : ""}`}
            onClick={() => setStatusFilter(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="filter-bar">
        <div className="form-group">
          <label htmlFor="filter_search">Search</label>
          <input
            id="filter_search"
            name="search"
            type="search"
            placeholder="Name, email, phone, brand"
            value={filters.search}
            onChange={(event) => setFilters((prev) => ({ ...prev, search: event.target.value }))}
          />
        </div>
        <div className="form-group">
          <label htmlFor="filter_status">Status</label>
          <select
            id="filter_status"
            name="status"
            value={filters.status}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, status: event.target.value, tab: event.target.value }))
            }
          >
            <option value="">All</option>
            <option value="New">New</option>
            <option value="In Progress">In Progress</option>
            <option value="Converted">Converted</option>
            <option value="Lost">Lost</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="filter_created_from">Created From</label>
          <input
            id="filter_created_from"
            name="created_from"
            type="date"
            value={filters.created_from}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, created_from: event.target.value }))
            }
          />
        </div>
        <div className="form-group">
          <label htmlFor="filter_created_to">Created To</label>
          <input
            id="filter_created_to"
            name="created_to"
            type="date"
            value={filters.created_to}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, created_to: event.target.value }))
            }
          />
        </div>
        <div className="filter-actions">
          <button type="button" className="btn btn-link" onClick={clearFilters}>
            Clear
          </button>
        </div>
      </div>

      <h2 className="section-heading">Add Lead</h2>
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange}
          />
        </div>
        <div className="form-group">
          <label htmlFor="phone">Phone</label>
          <input
            id="phone"
            name="phone"
            value={form.phone}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="name">Name</label>
          <input
            id="name"
            name="name"
            value={form.name}
            onChange={handleChange}
          />
        </div>
        <div className="form-group">
          <label htmlFor="address">Address</label>
          <input
            id="address"
            name="address"
            value={form.address}
            onChange={handleChange}
          />
        </div>
        <div className="form-group">
          <label htmlFor="brand_name">Brand Name</label>
          <input
            id="brand_name"
            name="brand_name"
            value={form.brand_name}
            onChange={handleChange}
          />
        </div>
        <div className="form-group">
          <label htmlFor="preferred_plan_id">Preferred Plan</label>
          <select
            id="preferred_plan_id"
            name="preferred_plan_id"
            value={form.preferred_plan_id}
            onChange={handleChange}
          >
            <option value="">Not Known / NA</option>
            {(plans || []).map((plan) => (
              <option key={plan.id} value={plan.id}>
                {plan.name}
              </option>
            ))}
          </select>
        </div>
        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <button type="submit" className="btn btn-primary" disabled={createLead.isPending}>
            {createLead.isPending ? "Saving..." : "Save Lead"}
          </button>
        </div>
      </form>

      <h2 className="section-heading" style={{ marginTop: 40 }}>
        Leads
      </h2>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Status</th>
            <th>Plan</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(leads || []).map((lead) => (
            <tr key={lead.id}>
              <td>{lead.name || "NA"}</td>
              <td>{lead.email || "NA"}</td>
              <td>{lead.phone || "NA"}</td>
              <td>
                <StatusBadge value={lead.status || "NA"} />
              </td>
              <td>{lead.preferred_plan_name || "NA"}</td>
              <td>{new Date(lead.created_at).toLocaleString()}</td>
              <td>
                <Link className="btn btn-primary" to={`/leads/${lead.id}`}>
                  View
                </Link>
              </td>
            </tr>
          ))}
          {(!leads || leads.length === 0) && (
            <tr>
              <td colSpan="6" style={{ textAlign: "center", padding: 40 }}>
                No leads yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default LeadsPage;

