import logging
import importlib
from mfr.renderer import FileRenderer

logger = logging.getLogger(__name__)

modules = [
    'image', 'pdf', 'pdb', 'code', 'ipynb', 'docx',
    'tabular.renderers',
]
for module in modules:
    try:
        importlib.import_module('mfr.renderer.' + module)
    except ImportError:
        logger.error('Could not import module {0}'.format(module))

config = {}


def detect(file_pointer):
    for name, cls in FileRenderer.registry.items():
        renderer = cls(**config.get(name, {}))
        if renderer._detect(file_pointer):
            return renderer
    return None


def render(file_pointer, *args, **kwargs):
    renderer = detect(file_pointer)
    if renderer is None:
        return None
    return renderer.render(file_pointer, *args, **kwargs)
