import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import TimeSeriesPage from './pages/TimeSeriesPage';
import VariationComparisonPage from './pages/VariationComparisonPage';

function Navigation() {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-primary to-secondary rounded-lg flex items-center justify-center">
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Precios
            </h1>
          </div>

          <div className="flex items-center gap-1">
            <Link
              to="/series"
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                isActive('/series')
                  ? 'bg-primary text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              Series de Tiempo
            </Link>
            <Link
              to="/variations"
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                isActive('/variations')
                  ? 'bg-primary text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              Variaciones
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <Routes>
          <Route path="/" element={<TimeSeriesPage />} />
          <Route path="/series" element={<TimeSeriesPage />} />
          <Route path="/variations" element={<VariationComparisonPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
