"""API routers package."""
import importlib

# Import blueprints from numbered folders using importlib
# Python doesn't allow direct imports of modules starting with numbers
# Use absolute import path instead of relative
ticker_000 = importlib.import_module('app.routers.000_ticker')
dcp_001 = importlib.import_module('app.routers.001_dcp')
cotizaciones_002 = importlib.import_module('app.routers.002_cotizaciones')
inflacion_dolares_003 = importlib.import_module('app.routers.003_inflacion_dolares')
prices_004 = importlib.import_module('app.routers.004_prices')
yield_curve_005 = importlib.import_module('app.routers.005_yield_curve')
data_export_006 = importlib.import_module('app.routers.006_data_export')
licitaciones_lrm_007 = importlib.import_module('app.routers.007_licitaciones_lrm')
update_008 = importlib.import_module('app.routers.008_update')

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