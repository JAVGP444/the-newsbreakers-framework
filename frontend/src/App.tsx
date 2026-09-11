import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import AnalysisPage from "./AnalysisPage";
import CnnLab from "./CnnLab";
import Observatory from "./Observatory";
import { TranslateProvider } from "./translate";

export default function App() {
  return (
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
          <Route path="/article/:id" element={<AnalysisPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </HashRouter>
    </TranslateProvider>
  );
}
