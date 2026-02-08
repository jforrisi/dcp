"""API routers package."""
import importlib.util
import sys
from pathlib import Path

# Import blueprints from numbered folders using importlib.util
# Python doesn't allow direct imports of modules starting with numbers
# Load modules directly from their __init__.py files

def load_module_from_path(module_name, folder_name):
    """Load a module from a numbered folder using file path."""
    routers_dir = Path(__file__).parent
    init_file = routers_dir / folder_name / '__init__.py'
    
    # Use full package path for sys.modules registration
    full_module_name = f'app.routers.{folder_name}'
    
    spec = importlib.util.spec_from_file_location(full_module_name, init_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {init_file}")
    
    module = importlib.util.module_from_spec(spec)
    
    # Register in sys.modules with full package name
    sys.modules[full_module_name] = module
    
    # Set __package__ and __name__ for relative imports to work
    module.__package__ = full_module_name
    module.__name__ = full_module_name
    module.__file__ = str(init_file)
    
    # Execute the module
    spec.loader.exec_module(module)
    
    return module

ticker_000 = load_module_from_path('ticker_000', '000_ticker')
dcp_001 = load_module_from_path('dcp_001', '001_dcp')
cotizaciones_002 = load_module_from_path('cotizaciones_002', '002_cotizaciones')
inflacion_dolares_003 = load_module_from_path('inflacion_dolares_003', '003_inflacion_dolares')
prices_004 = load_module_from_path('prices_004', '004_prices')
yield_curve_005 = load_module_from_path('yield_curve_005', '005_yield_curve')
data_export_006 = load_module_from_path('data_export_006', '006_data_export')
licitaciones_lrm_007 = load_module_from_path('licitaciones_lrm_007', '007_licitaciones_lrm')
update_008 = load_module_from_path('update_008', '008_update')

# Export modules/blueprints with original names for backward compatibility
# ticker module exports a blueprint named 'ticker'
ticker = ticker_000
# Other modules export 'bp' blueprint - export the modules themselves
dcp = dcp_001
cotizaciones = cotizaciones_002
inflacion_dolares = inflacion_dolares_003
prices = prices_004
yield_curve = yield_curve_005
# data_export exports the blueprint directly
data_export = data_export_006.data_export
licitaciones_lrm = licitaciones_lrm_007
update = update_008