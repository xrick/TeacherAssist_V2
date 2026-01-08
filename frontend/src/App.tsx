// frontend/src/App.tsx
import { Routes, Route } from "react-router-dom";
import GeneratorPage from "./components/GeneratorPage";

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <Routes>
        <Route path="/" element={<GeneratorPage />} />
      </Routes>
    </div>
  );
}

export default App;
