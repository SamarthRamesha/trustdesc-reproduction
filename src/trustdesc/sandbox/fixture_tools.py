"""Newly authored SYNTHETIC tools. No filesystem, network, subprocess or imports
of research artifacts. Fixed bounded operations permit safe host fixture tests.
"""

SCHEMAS = {
    'apply_formula': {'type': 'object', 'properties': {'formula': {'type': 'string'}}, 'required': ['formula']},
    'normalize_name': {'type': 'object', 'properties': {'name': {'type': 'string'}}, 'required': ['name']},
}


def apply_formula(formula: str):
    if not formula.startswith('='):
        raise ValueError('Formula must start with =')
    if any(x in formula.upper() for x in ('INDIRECT', 'HYPERLINK')):
        raise ValueError('Unsafe formula blocked')
    return {'accepted_formula': formula}


def normalize_name(name: str):
    return {'normalized': name.strip().lower()}


def invoke(tool: str, arguments: dict):
    # Never accept a callable, module path or executable from input.
    if tool not in SCHEMAS or not isinstance(arguments, dict):
        raise ValueError('Unknown fixture tool or invalid arguments')
    key = 'formula' if tool == 'apply_formula' else 'name'
    if set(arguments) != {key} or not isinstance(arguments[key], str) or len(arguments[key]) > 4096:
        raise ValueError('Invalid fixture argument shape/type/size')
    if tool == 'apply_formula':
        return apply_formula(arguments['formula'])
    return normalize_name(arguments['name'])
