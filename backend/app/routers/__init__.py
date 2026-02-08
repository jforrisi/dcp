"""API routers package."""
import importlib

# Import blueprints from numbered folders using importlib
# Python doesn't allow direct imports of modules starting with numbers
ticker_000 = importlib.import_module('.000_ticker', package=__name__)
dcp_001 = importlib.import_module('.001_dcp', package=__name__)
cotizaciones_002 = importlib.import_module('.002_cotizaciones', package=__name__)
inflacion_dolares_003 = importlib.import_module('.003_inflacion_dolares', package=__name__)
prices_004 = importlib.import_module('.004_prices', package=__name__)
yield_curve_005 = importlib.import_module('.005_yield_curve', package=__name__)
data_export_006 = importlib.import_module('.006_data_export', package=__name__)
licitaciones_lrm_007 = importlib.import_module('.007_licitaciones_lrm', package=__name__)
update_008 = importlib.import_module('.008_update', package=__name__)

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