// Componente de Selector de Mes/Año
function MonthYearPicker({ fechaDesde, fechaHasta, onFechaDesdeChange, onFechaHastaChange }) {
    // Convertir fecha completa (YYYY-MM-DD) a formato mes (YYYY-MM)
    const toMonthFormat = (fecha) => {
        if (!fecha) return '';
        return fecha.substring(0, 7); // Toma YYYY-MM
    };

    // Convertir formato mes (YYYY-MM) a fecha completa
    const fromMonthFormat = (monthValue, isEnd = false) => {
        if (!monthValue) return '';
        if (isEnd) {
            // Para "hasta", usar el último día del mes
            const [year, month] = monthValue.split('-');
            const lastDay = new Date(year, month, 0).getDate();
            return `${year}-${month}-${String(lastDay).padStart(2, '0')}`;
        } else {
            // Para "desde", usar el primer día del mes
            return `${monthValue}-01`;
        }
    };

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Desde (Mes/Año)
                </label>
                <input
                    type="month"
                    value={toMonthFormat(fechaDesde)}
                    onChange={(e) => onFechaDesdeChange(fromMonthFormat(e.target.value, false))}
                    className="input-field"
                />
            </div>
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Hasta (Mes/Año)
                </label>
                <input
                    type="month"
                    value={toMonthFormat(fechaHasta)}
                    onChange={(e) => onFechaHastaChange(fromMonthFormat(e.target.value, true))}
                    className="input-field"
                />
            </div>
        </div>
    );
}
