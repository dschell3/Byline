import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router';
import './index.css';
import AppLayout from './components/AppLayout.tsx';
import RequireAuth from './components/RequireAuth.tsx';
import HomePage from './pages/HomePage.tsx';
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
        <Route path="/tokens" element={<TokensPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
