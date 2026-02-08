// Componente de Selector de Rango de Fechas (fecha completa ddmmyyyy)
function DateRangePicker({ fechaDesde, fechaHasta, onFechaDesdeChange, onFechaHastaChange }) {
    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Desde
                </label>
                <input
                    type="date"
                    value={fechaDesde}
                    onChange={(e) => onFechaDesdeChange(e.target.value)}
                    className="input-field w-full"
                />
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Hasta
                </label>
                <input
                    type="date"
                    value={fechaHasta}
                    onChange={(e) => onFechaHastaChange(e.target.value)}
                    className="input-field w-full"
                />
            </div>
        </div>
    );
}
