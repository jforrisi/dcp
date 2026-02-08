"""Admin panel blueprints."""
from flask import Blueprint

bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Importar y registrar todos los sub-blueprints
# Cada blueprint aplica su propio middleware @admin_only
from . import familia, sub_familia, variables, graph, filtros, maestro, pais_grupo, tipo_serie

# Registrar todos los sub-blueprints
bp.register_blueprint(familia.bp)
bp.register_blueprint(sub_familia.bp)
bp.register_blueprint(variables.bp)
bp.register_blueprint(graph.bp)
bp.register_blueprint(filtros.bp)
bp.register_blueprint(maestro.bp)
bp.register_blueprint(pais_grupo.bp)
bp.register_blueprint(tipo_serie.bp)