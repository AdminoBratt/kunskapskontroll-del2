import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import AskPage from './pages/AskPage';
import SearchPage from './pages/SearchPage';
import UploadPage from './pages/UploadPage';
import LibraryPage from './pages/LibraryPage';
import InfoPage from './pages/InfoPage';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/ask" replace />} />
          <Route path="/ask" element={<AskPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/info" element={<InfoPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
