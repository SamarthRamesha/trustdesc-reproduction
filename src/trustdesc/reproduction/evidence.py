"""Source evidence validation and iterative, execution-grounded refinement."""
from __future__ import annotations
import ast
import copy
from trustdesc.common.io import ValidationError, digest
from trustdesc.descgen import generate
from trustdesc.descgen.generate import validate_description, prose_paths
from trustdesc.descgen.sanitize import sanitize, check_mapping
from trustdesc.descgen.prompts import BOUNDARY
from trustdesc.dynver import verify
from trustdesc.common.io import require_fields, nonempty

GENERATE_COMPACT = BOUNDARY + '''Describe only the behavior implemented by the supplied
Python code. Return exactly three fields: "summary" (string), "functionalities"
(list of strings), and "input_schema" (JSON Schema object).
Copy the supplied input_schema_template exactly, adding a concise description
to each parameter property. Keep its original parameter names, types and required
list even if identifiers in the reasoning code were renamed. Do not invent
features, guarantees, or arguments. Do not describe the analysis framework.
Return no claims field; claim bookkeeping is constructed mechanically from your
exact prose afterward. Include input constraints, return behavior and observable
side effects where the implementation supports them. Keep prose concise.'''

GROUND = BOUNDARY + '''Link each listed claim to the supplied original functions.
Return one JSON object with an "evidence" list. Every record has "claim_id"
(copy an actual supplied claim id), "references" (list of objects with only a
"function" key containing an exact key from supplied functions), and "rationale"
(explain the relationship to this specific claim).
Do not generate source quotes: the pipeline attaches the complete referenced
function and its hash/span automatically. An empty references list means the
claim lacks implementation support. Cover each claim once and use no invented
function names. This is source attribution, not a proof of semantic truth.'''

REFINE = BOUNDARY + '''Correct the description using only the supplied actual traces
and source evidence. Remove unsupported claims; correct false input descriptions
when execution establishes a counterexample. Preserve the validated structural
input schema. Return the same complete description format (summary,
functionalities,input_schema,claims), with exactly one matching claim per prose
field. No capability may be added without evidence. Corrections are candidates
and will be executed and judged again, never accepted without retesting.'''


def interface(slice_result):
    entry = slice_result['entry']
    source = slice_result.get('evidence_spans', {}).get(entry, {}).get('source')
    if not source:
        raise ValidationError('Entry source evidence missing')
    node = ast.parse(source).body[0]
    args = node.args.posonlyargs + node.args.args
    defaults = [None] * (len(args) - len(node.args.defaults)) + list(node.args.defaults)
    pairs = list(zip(args, defaults)) + list(zip(node.args.kwonlyargs, node.args.kw_defaults))
    properties, required = {}, []
    for arg, default in pairs:
        if arg.arg in {'self', 'cls'}:
            continue
        typ = {'str': 'string', 'int': 'integer', 'float': 'number', 'bool': 'boolean', 'dict': 'object', 'list': 'array'}.get(ast.unparse(arg.annotation) if arg.annotation else '')
        properties[arg.arg] = {'type': typ} if typ else {}
        if default is None:
            required.append(arg.arg)
    return {'type': 'object', 'properties': properties, 'required': required,
            'has_variadic': bool(node.args.vararg or node.args.kwarg),
            'positional_only': [a.arg for a in node.args.posonlyargs],
            'certification': 'static_signature_only; types/constraints/return behavior not proven'}


def check_schema(description, signature):
    schema = description['input_schema']
    if not signature['has_variadic'] and set(schema['properties']) != set(signature['properties']):
        raise ValidationError('Generated argument names disagree with exposed implementation')
    if set(schema.get('required', [])) != set(signature['required']):
        raise ValidationError('Required arguments disagree with exposed implementation')
    for name, prop in signature['properties'].items():
        if prop.get('type') and schema['properties'][name].get('type') != prop['type']:
            raise ValidationError('Generated argument type disagrees with simple annotation')


def validate_evidence(response, description, spans):
    rows = response.get('evidence')
    claims = {c['id'] for c in description['claims']}
    if not isinstance(rows, list) or len(rows) != len(claims) or {r.get('claim_id') for r in rows} != claims:
        raise ValidationError('Evidence must cover each claim once')
    for row in rows:
        if not isinstance(row.get('references'), list) or not isinstance(row.get('rationale'), str):
            raise ValidationError('Malformed source evidence')
        for ref in row['references']:
            span = spans.get(ref.get('function'))
            if span and 'quote' not in ref:
                ref['quote'] = span['source']
            if not span or not isinstance(ref.get('quote'), str) or not ref['quote'].strip() or ref['quote'] not in span['source']:
                raise ValidationError('Invented source evidence rejected')
            ref.update(path=span['path'], file_sha256=span['file_sha256'], line_start=span['line_start'], line_end=span['line_end'])
        row['confidence'] = 'model_attributed_source_and_finite_tests_required'
    return rows


def grounded_generate(slice_result, model):
    signature = interface(slice_result)
    template = {k: copy.deepcopy(signature[k]) for k in ['type','properties','required']}
    sanitized = sanitize(slice_result['source'], IdentifierGuard(model))
    generated = model.complete('description', GENERATE_COMPACT,
                   {'tool': slice_result['tool'], 'entry': slice_result['entry'], 'code': sanitized['source'],
                    'input_schema_template': template})
    if not isinstance(generated, dict) or set(generated) - {'summary','functionalities','input_schema','claims'}:
        raise ValidationError('Unexpected generated description fields')
    description = {k: copy.deepcopy(generated[k]) for k in ['summary','functionalities','input_schema']}
    # No semantic content is invented: each claim copies a generated prose field
    # exactly. Avoid asking small models to repeat their own strings/JSON paths.
    description['claims'] = [{'id': 'c'+str(i+1), 'text': text, 'target': list(path)}
                             for i,(path,text) in enumerate(prose_paths(description).items())]
    validate_description(description)
    draft = {'description': description, 'sanitized': sanitized,
             'model': model.model_id, 'model_mode': model.mode, 'status': 'unverified_draft',
             'prompt_hash': digest(GENERATE_COMPACT), 'claim_decomposition': 'mechanical_exact_prose_fields_no_semantic_replacement'}
    check_schema(draft['description'], signature)
    attributed = model.complete('source_grounding', GROUND,
                    {'claims': draft['description']['claims'], 'functions': slice_result['evidence_spans']})
    evidence = validate_evidence(attributed, draft['description'], slice_result['evidence_spans'])
    draft.update(source_evidence=evidence, implementation_interface=signature,
                 semantic_consistency='signature_and_exact_source_quotes_checked; entailment_model_assessed')
    return draft


def iterative_verify(description, model, runner, slice_result, *, max_rounds=2, source_evidence=None):
    if not 1 <= max_rounds <= 4:
        raise ValidationError('Refinement rounds must be 1..4')
    current = copy.deepcopy(description)
    history = []
    current_evidence = copy.deepcopy(source_evidence) if source_evidence is not None else None
    signature = interface(slice_result)
    for iteration in range(max_rounds):
        checked = verify(current, VerificationGuard(model), runner)
        if current_evidence is not None:
            grounded = {r['claim_id'] for r in current_evidence if r['references']}
            excluded = []
            for decision in checked['decisions']:
                if decision['claim_id'] not in grounded:
                    decision.update(verdict='inconclusive', reason='No validated source reference')
                    excluded.append(decision['claim_id'])
            from trustdesc.dynver.verify import filter_description
            checked['full'] = filter_description(current, checked['decisions'])
            checked['lite'] = {k: copy.deepcopy(v) for k,v in checked['full'].items() if k not in {'functionalities','claims'}}
            checked['usable_summary'] = bool(checked['full']['summary'])
            checked['source_grounding_exclusions'] = excluded
            checked['source_evidence'] = copy.deepcopy(current_evidence)
        history.append({'round': iteration + 1, 'input_description': copy.deepcopy(current), 'verification': copy.deepcopy(checked)})
        if all(d['verdict'] == 'supported' for d in checked['decisions']):
            break
        # Environment errors cannot establish corrections or refutations.
        if iteration + 1 == max_rounds or not any(d['verdict'] == 'refuted' for d in checked['decisions']):
            break
        try:
            proposal = model.complete('refinement', REFINE,
                        {'description': current, 'decisions': checked['decisions'], 'traces': checked['traces'],
                         'functions': slice_result['evidence_spans'], 'interface': signature})
            validate_description(proposal)
            check_schema(proposal, signature)
            if digest(proposal) == digest(current):
                history[-1]['refinement_status'] = 'unchanged'
                break
            history[-1]['refinement_status'] = 'candidate_requires_next_round'
            if current_evidence is not None:
                attributed = model.complete('source_grounding', GROUND,
                        {'claims': proposal['claims'], 'functions': slice_result['evidence_spans']})
                current_evidence = validate_evidence(attributed, proposal, slice_result['evidence_spans'])
            current = proposal
        except Exception as exc:
            history[-1]['refinement_status'] = 'rejected'
            history[-1]['refinement_error'] = f'{type(exc).__name__}: {exc}'
            break
    checked.update(history=history, refinement_rounds=len(history),
                   convergence='all_claims_supported_on_observations' if all(d['verdict'] == 'supported' for d in checked['decisions']) else 'stopped_with_explicit_uncertainty',
                   confidence='finite_observations_only',
                   structural_schema_status='static_signature_checked; nested constraints and return schema not certified')
    return checked


class IdentifierGuard:
    """Explain invalid classifier mappings to the same real model once."""
    def __init__(self, model):
        self.model = model

    def complete(self, stage, system, payload):
        response = self.model.complete(stage, system, payload)
        try:
            renames = response.get('renames')
            if not isinstance(renames, dict) or not set(renames).issubset(payload['identifiers']):
                raise ValidationError('Unknown identifiers or malformed rename mapping')
            check_mapping(set(payload['identifiers']), renames)
            return response
        except ValidationError as exc:
            return self.model.complete(stage, system + '\nYour previous mapping was rejected. Preserve neutral identifiers; every final name must be unique including unchanged identifiers. Return only necessary promotional-term removals.',
                        {**payload, 'rejected_mapping': response, 'validation_error': str(exc)})


class VerificationGuard:
    """Bounded validation-feedback retry; never invents a task or verdict."""
    def __init__(self, model):
        self.model = model
        self.model_id, self.mode = model.model_id, model.mode

    def complete(self, stage, system, payload):
        response = self.model.complete(stage, system, payload)
        try:
            if stage == 'verification_plan':
                require_fields(response, {'tasks'}, 'verification plan')
                if not isinstance(response['tasks'], list):
                    raise ValidationError('tasks must be a list')
                expected = {c['id'] for c in payload['description']['claims']}
                seen = set()
                for task in response['tasks']:
                    require_fields(task, {'claim_id','verifiable','task','reason'}, 'verification task')
                    if task['claim_id'] not in expected or task['claim_id'] in seen or type(task['verifiable']) is not bool:
                        raise ValidationError('Exactly one task per actual claim id and boolean verifiable are required')
                    seen.add(task['claim_id'])
                    nonempty(task['reason'], 'reason')
                    if task['verifiable']:
                        nonempty(task['task'], 'task')
                    elif task['task'] is not None:
                        raise ValidationError('If verifiable=false, task MUST be JSON null; never a string')
                if seen != expected:
                    raise ValidationError('Verification plan omitted actual claim ids')
            elif stage == 'judge':
                require_fields(response, {'verdict','reason'}, 'judge')
                if response['verdict'] not in {'supported','refuted','inconclusive'}:
                    raise ValidationError('verdict must be supported, refuted or inconclusive')
                nonempty(response['reason'], 'reason')
            return response
        except (ValidationError, TypeError, KeyError) as exc:
            return self.model.complete(stage, system + '\nYour previous response failed protocol validation. Correct its format using the actual diagnostic. Do not fabricate an observation or verdict.',
                       {**payload,'rejected_response':response,'validation_error':str(exc)})
