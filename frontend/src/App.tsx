import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import AnalysisPage from "./AnalysisPage";
import CnnLab from "./CnnLab";
import Login from "./Login";
import Observatory from "./Observatory";
import Preview from "./Preview";
import { LicenseProvider, useLicense } from "./license";
import { TranslateProvider } from "./translate";

function Gate() {
  const { licensed, signedIn, loading } = useLicense();
  if (loading) {
    return (
      <div className="shell">
        <p className="muted">Abriendo…</p>
      </div>
    );
  }
  if (!signedIn) {
    return <Login />;
  }
  if (!licensed) {
    return <Preview />;
  }
  return (
    <Routes>
      <Route path="/" element={<Observatory />} />
      <Route path="/sala" element={<Observatory />} />
      <Route path="/revision" element={<Observatory />} />
      <Route path="/mapa" element={<Observatory />} />
      <Route path="/graficas" element={<Observatory />} />
      <Route path="/grafo" element={<Observatory />} />
      <Route path="/fuentes" element={<Observatory />} />
      <Route path="/cnn" element={<CnnLab />} />
      <Route path="/article/:id" element={<AnalysisPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <TranslateProvider>
      <LicenseProvider>
        <HashRouter>
          <Gate />
        </HashRouter>
      </LicenseProvider>
    </TranslateProvider>
  );
}
