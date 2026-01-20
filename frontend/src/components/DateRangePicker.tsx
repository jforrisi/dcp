import { useState } from 'react';

interface DateRangePickerProps {
  fechaDesde: string;
  fechaHasta: string;
  onFechaDesdeChange: (date: string) => void;
  onFechaHastaChange: (date: string) => void;
}

export default function DateRangePicker({
  fechaDesde,
  fechaHasta,
  onFechaDesdeChange,
  onFechaHastaChange,
}: DateRangePickerProps) {
  const today = format(new Date(), 'yyyy-MM-dd');

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Fecha Desde
        </label>
        <input
          type="date"
          value={fechaDesde}
          onChange={(e) => onFechaDesdeChange(e.target.value)}
          max={fechaHasta || today}
          className="input-field"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Fecha Hasta
        </label>
        <input
          type="date"
          value={fechaHasta}
          onChange={(e) => onFechaHastaChange(e.target.value)}
          min={fechaDesde}
          max={today}
          className="input-field"
        />
      </div>
    </div>
  );
}
