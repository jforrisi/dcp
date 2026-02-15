// App Principal
function App() {
    const [currentPage, setCurrentPage] = React.useState('home');

    // Escuchar eventos de navegación desde HomePage
    React.useEffect(() => {
        const handleNavigate = (event) => {
            setCurrentPage(event.detail.moduleId);
        };
        window.addEventListener('navigateToModule', handleNavigate);
        return () => window.removeEventListener('navigateToModule', handleNavigate);
    }, []);

    return (
        <div className="min-h-screen bg-gray-50">
            <Navigation currentPage={currentPage} onPageChange={setCurrentPage} />
            {currentPage === 'home' && <HomePage />}
            {(currentPage === 'dcp' || currentPage === 'series') && <DCPPage />}
            {currentPage === 'cotizaciones' && <CotizacionesPage />}
            {currentPage === 'inflacion-dolares' && <InflacionDolaresPage />}
            {currentPage === 'yield-curve' && <YieldCurvePage />}
            {currentPage === 'inflacion-implicita' && <InflacionImplicitaPage />}
            {currentPage === 'data-export' && <DataExportPage />}
            {currentPage === 'licitaciones-lrm' && <LicitacionesLRMPage />}
            {currentPage === 'politica-monetaria' && <PoliticaMonetariaPage />}
        </div>
    );
}

// Renderizar la app
ReactDOM.render(<App />, document.getElementById('root'));
