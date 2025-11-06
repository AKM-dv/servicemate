import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import LeadsPage from "./pages/LeadsPage.jsx";
import LeadDetailPage from "./pages/LeadDetailPage.jsx";
import PlansPage from "./pages/PlansPage.jsx";
import InvoicesPage from "./pages/InvoicesPage.jsx";
import FeedbackPage from "./pages/FeedbackPage.jsx";
import InvoicePreviewPage from "./pages/InvoicePreviewPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RequireAuth from "./components/RequireAuth.jsx";

const App = () => (
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route element={<RequireAuth />}>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/leads" element={<LeadsPage />} />
        <Route path="/leads/:leadId" element={<LeadDetailPage />} />
        <Route path="/plans" element={<PlansPage />} />
        <Route path="/invoices" element={<InvoicesPage />} />
        <Route path="/invoice-preview" element={<InvoicePreviewPage />} />
        <Route path="/feedback" element={<FeedbackPage />} />
      </Route>
    </Route>
    <Route path="*" element={<Navigate to="/dashboard" replace />} />
  </Routes>
);

export default App;

