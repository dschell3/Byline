import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router';
import './index.css';
import App from './App.tsx';
import TokensPage from './pages/TokensPage.tsx';
import SignInPage from './pages/SignInPage.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/signin" element={<SignInPage />} />
        <Route
          path="/forgot"
          element={<p className="p-8 text-xl">Forgot password (placeholder)</p>}
        />
        <Route path="/tokens" element={<TokensPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
