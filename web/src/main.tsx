import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router';
import './index.css';
import App from './App.tsx';
import RequireAuth from './components/RequireAuth.tsx';
import SignInPage from './pages/SignInPage.tsx';
import TokensPage from './pages/TokensPage.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Signed-in pages go inside RequireAuth (SCRUM-13). */}
        <Route element={<RequireAuth />}>
          <Route path="/" element={<App />} />
        </Route>
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/tokens" element={<TokensPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
