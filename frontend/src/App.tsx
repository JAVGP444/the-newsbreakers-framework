import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import AnalysisPage from "./AnalysisPage";
import CnnLab from "./CnnLab";
import Observatory from "./Observatory";
import { LocaleProvider } from "./locale";
import { TranslateProvider } from "./translate";

export default function App() {
  return (
    <LocaleProvider>
      <TranslateProvider>
        <HashRouter>
          <Routes>
            <Route path="/" element={<Observatory />} />
            <Route path="/sala" element={<Observatory />} />
            <Route path="/revision" element={<Observatory />} />
            <Route path="/mapa" element={<Observatory />} />
            <Route path="/graficas" element={<Observatory />} />
            <Route path="/grafo" element={<Observatory />} />
            <Route path="/fuentes" element={<Observatory />} />
            <Route path="/cnn" element={<CnnLab />} />
            <Route path="/narrativas" element={<Navigate to="/" replace />} />
            <Route path="/afirmaciones" element={<Navigate to="/revision" replace />} />
            <Route path="/evidencia" element={<Navigate to="/revision" replace />} />
            <Route path="/alertas" element={<Navigate to="/revision" replace />} />
            <Route path="/bancos" element={<Navigate to="/fuentes" replace />} />
            <Route path="/article/:id" element={<AnalysisPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </HashRouter>
      </TranslateProvider>
    </LocaleProvider>
  );
}
