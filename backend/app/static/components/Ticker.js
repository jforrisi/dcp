// Componente Ticker estilo Wall Street
function Ticker({ data = [] }) {
    const tickerRef = React.useRef(null);
    const animationRef = React.useRef(null);
    const positionRef = React.useRef(0);
    const [isPaused, setIsPaused] = React.useState(false);

    // Duplicar datos para crear efecto de loop infinito
    const tickerItems = React.useMemo(() => {
        if (!data || data.length === 0) return [];
        // Duplicar los datos 2 veces para crear un loop suave
        return [...data, ...data];
    }, [data]);

    // Animación del ticker
    React.useEffect(() => {
        if (!tickerRef.current || tickerItems.length === 0 || isPaused) return;

        const ticker = tickerRef.current;
        
        const animate = () => {
            if (isPaused) return;
            
            positionRef.current -= 0.5; // Velocidad de desplazamiento
            ticker.style.transform = `translateX(${positionRef.current}px)`;

            // Resetear posición cuando se completa un ciclo
            const tickerWidth = ticker.scrollWidth;
            if (Math.abs(positionRef.current) >= tickerWidth / 2) {
                positionRef.current = 0;
            }

            animationRef.current = requestAnimationFrame(animate);
        };

        animationRef.current = requestAnimationFrame(animate);

        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [tickerItems, isPaused]);

    if (!data || data.length === 0) {
        return null;
    }

    return (
        <div 
            className="bg-gray-900 text-white py-2 overflow-hidden relative"
            onMouseEnter={() => setIsPaused(true)}
            onMouseLeave={() => setIsPaused(false)}
        >
            <div 
                className="flex items-center whitespace-nowrap" 
                ref={tickerRef}
                style={{ willChange: 'transform' }}
            >
                {tickerItems.map((item, index) => (
                    <div
                        key={`${item.pais}-${item.variable}-${index}`}
                        className="flex items-center mx-6 px-4 py-1 border-r border-gray-700 flex-shrink-0"
                    >
                        <span className="font-semibold text-green-400 mr-2">{item.pais}</span>
                        <span className="text-gray-300 mr-2">{item.variable}:</span>
                        <span className="font-bold text-white text-lg">{item.valor_formateado}</span>
                        <span className="text-xs text-gray-400 ml-2">
                            {(() => {
                                // Formatear fecha manualmente para evitar problemas de timezone
                                const fechaStr = item.fecha;
                                if (!fechaStr) return '';
                                const partes = fechaStr.split('-');
                                if (partes.length === 3) {
                                    const dia = partes[2].padStart(2, '0');
                                    const mes = partes[1].padStart(2, '0');
                                    const año = partes[0].slice(-2); // Últimos 2 dígitos del año
                                    return `${dia}/${mes}/${año}`;
                                }
                                return fechaStr;
                            })()}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}
