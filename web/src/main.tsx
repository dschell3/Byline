import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router';
import './index.css';
import AppLayout from './components/AppLayout.tsx';
import RequireAuth from './components/RequireAuth.tsx';
import HomePage from './pages/HomePage.tsx';
import InvitePage from './pages/InvitePage.tsx';
import SignInPage from './pages/SignInPage.tsx';
import TokensPage from './pages/TokensPage.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Signed-in pages go inside RequireAuth (SCRUM-13). */}
        <Route element={<RequireAuth />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomePage />} />
          </Route>
        </Route>
        <Route path="/signin" element={<SignInPage />} />
        {/* P05: a new intern's invite link (SCRUM-11). Public; signs the browser in on success. */}
        <Route path="/invite/:token" element={<InvitePage />} />
        {/* Linked from P05. Placeholders until the legal copy has a card. */}
        <Route path="/terms" element={<p className="p-8 text-xl">Terms (placeholder)</p>} />
        <Route
          path="/privacy"
          element={<p className="p-8 text-xl">Privacy notice (placeholder)</p>}
        />
        <Route path="/tokens" element={<TokensPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
