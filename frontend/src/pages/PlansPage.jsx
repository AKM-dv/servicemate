import { useQuery } from "@tanstack/react-query";
import apiClient from "../services/apiClient.js";

const PlansPage = () => {
  const { data: plans, isLoading } = useQuery({
    queryKey: ["plans"],
    queryFn: () => apiClient.get("/plans").then((res) => res.data),
  });

  const plan = plans?.[0];

  return (
    <div className="plans-page">
      <h2 className="section-heading">Basic Subscription</h2>
      <div className="card plan-card">
        {isLoading ? (
          <div>Loading plan...</div>
        ) : (
          <>
            <div className="plan-price">
              <span className="plan-price-currency">INR</span>
              <span className="plan-price-value">{Number(plan?.price || 1999).toLocaleString("en-IN")}</span>
              <span className="plan-price-period">per month</span>
            </div>
            <p className="plan-description">
              Launch your branded Service Mate experience with a unified web, Android, and iOS presence, complete with lead management and SEO essentials.
            </p>
            <ul className="plan-feature-list">
              {(plan?.features || [
                "Responsive Website",
                "Android App",
                "iOS App",
                "Elementary SEO",
                "Lead Management",
              ]).map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
            <div className="plan-cta">
              <button className="btn btn-primary" type="button" disabled>
                Coming Soon
              </button>
              <span className="plan-note">Customisations available on request.</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default PlansPage;

