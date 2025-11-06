import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "../services/apiClient.js";
import StatusBadge from "../components/StatusBadge.jsx";

const categories = ["Bug", "Suggestion", "Improvement", "Other"];
const statuses = ["Open", "In Review", "Resolved"];

const feedbackInitial = {
  title: "",
  body: "",
  category: "Suggestion",
};

const FeedbackPage = () => {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(feedbackInitial);

  const { data: feedbackItems, isLoading } = useQuery({
    queryKey: ["feedback"],
    queryFn: () => apiClient.get("/feedback").then((res) => res.data),
  });

  const createFeedback = useMutation({
    mutationFn: (payload) => apiClient.post("/feedback", payload).then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feedback"] });
      setForm(feedbackInitial);
    },
  });

  const updateFeedback = useMutation({
    mutationFn: ({ id, data }) => apiClient.put(`/feedback/${id}`, data).then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feedback"] });
    },
  });

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const submitFeedback = (event) => {
    event.preventDefault();
    createFeedback.mutate({
      title: form.title,
      body: form.body,
      category: form.category,
    });
  };

  const handleStatusChange = (id, status) => {
    updateFeedback.mutate({ id, data: { status } });
  };

  return (
    <div>
      <h2 className="section-heading">Admin Feedback Board</h2>
      <form className="form-grid" onSubmit={submitFeedback}>
        <div className="form-group">
          <label htmlFor="title">Title</label>
          <input id="title" name="title" value={form.title} onChange={handleChange} required />
        </div>
        <div className="form-group">
          <label htmlFor="category">Category</label>
          <select id="category" name="category" value={form.category} onChange={handleChange}>
            {categories.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group" style={{ gridColumn: "1 / -1" }}>
          <label htmlFor="body">Details</label>
          <textarea
            id="body"
            name="body"
            rows="4"
            value={form.body}
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <button className="btn btn-primary" type="submit" disabled={createFeedback.isPending}>
            {createFeedback.isPending ? "Saving..." : "Add Entry"}
          </button>
        </div>
      </form>

      <h2 className="section-heading" style={{ marginTop: 40 }}>
        Logged Items
      </h2>
      {isLoading ? (
        <div>Loading feedback...</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Category</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {(feedbackItems || []).map((item) => (
              <tr key={item.id}>
                <td>
                  <div style={{ fontWeight: 600 }}>{item.title}</div>
                  <div style={{ color: "#475569", marginTop: 6 }}>{item.body}</div>
                </td>
                <td>
                  <StatusBadge value={item.category} />
                </td>
                <td>
                  <StatusBadge value={item.status} />
                </td>
                <td>{item.created_at ? new Date(item.created_at).toLocaleString() : "--"}</td>
                <td>
                  <select
                    value={item.status}
                    onChange={(event) => handleStatusChange(item.id, event.target.value)}
                  >
                    {statuses.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {(!feedbackItems || feedbackItems.length === 0) && (
              <tr>
                <td colSpan="5" style={{ textAlign: "center", padding: 40 }}>
                  No feedback items yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default FeedbackPage;

