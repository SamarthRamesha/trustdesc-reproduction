"""Free local inference. Safetensors only; no remote code or paid endpoints."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import time
from trustdesc.common.io import canonical, digest
from trustdesc.common.models import ModelError


def json_object(text):
    text = text.strip()
    if text.startswith('```') and text.endswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)[:-3].strip()
    try:
        value = json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON constant')))
    except ValueError as exc:
        raise ModelError('Invalid JSON; raw output saved in call record') from exc
    if not isinstance(value, dict):
        raise ModelError('Expected a JSON object')
    return value


class LocalModel:
    mode = 'real_local_transformers_inference'

    def __init__(self, config, cache):
        import torch
        import transformers
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if not re.fullmatch('[0-9a-f]{40}', config['revision']):
            raise ModelError('Full immutable model revision required')
        self.cfg = config
        self.model_id = config['model_id']
        self.audit = []
        self.torch = torch
        self.device = config.get('device', 'cpu')
        if self.device not in {'cpu', 'cuda'}:
            raise ModelError('Unsupported explicit inference device')
        if self.device == 'cuda' and not torch.cuda.is_available():
            raise ModelError('CUDA selected but PyTorch cannot use it; no silent CPU execution of the larger model')
        if self.device == 'cpu':
            torch.set_num_threads(min(4, torch.get_num_threads()))
        snapshot = Path(snapshot_download(self.model_id, revision=config['revision'], cache_dir=str(cache),
                        token=False, allow_patterns=['*.json', '*.safetensors', '*.txt', '*.model', '*.tiktoken']))
        assets = {}
        for path in sorted(snapshot.rglob('*')):
            if path.is_file():
                h = hashlib.sha256()
                with path.open('rb') as f:
                    for block in iter(lambda: f.read(4*1024*1024), b''):
                        h.update(block)
                assets[path.relative_to(snapshot).as_posix()] = {'sha256': h.hexdigest(), 'bytes': path.stat().st_size}
        self.tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False)
        self.model = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False,
                    use_safetensors=True, torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                    attn_implementation='eager').to(self.device).eval()
        self.runtime = {'model_id': self.model_id, 'revision': config['revision'], 'device': self.device,
                        'torch': torch.__version__, 'transformers': transformers.__version__, 'assets': assets,
                        'precision': 'float16' if self.device == 'cuda' else 'float32',
                        'integrity': 'immutable HF commit over TLS; observed asset SHA-256; no separate signed publisher manifest',
                        'paper_equivalence': False, 'api_cost_usd': 0.0, 'compute_cost_usd': None}

    def complete(self, stage, system, payload):
        messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': canonical(payload)}]
        inputs = self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                    return_dict=True, return_tensors='pt').to(self.device)
        count = inputs['input_ids'].shape[-1]
        record = {'stage': stage, 'messages': messages, 'request_hash': digest(messages),
                  'input_tokens': count, 'output_tokens': None, 'model': self.model_id,
                  'revision': self.cfg['revision'], 'cost_usd': 0.0, 'compute_cost_usd': None,
                  'status': 'started', 'temperature': self.cfg.get('temperature', .2)}
        self.audit.append(record)
        if count > self.cfg.get('max_input_tokens', 4096):
            record['status'] = 'context_limit'
            raise ModelError(f'Input has {count} tokens, beyond context cap; no truncation')
        seed = (self.cfg.get('seed', 42) + int(digest(messages)[:8], 16)) % (2**31)
        self.torch.manual_seed(seed)
        start = time.perf_counter()
        try:
            if self.device == 'cuda':
                self.torch.cuda.synchronize()
            with self.torch.inference_mode():
                output = self.model.generate(**inputs, do_sample=True, temperature=self.cfg.get('temperature', .2),
                    max_new_tokens=self.cfg.get('max_new_tokens', 1600), pad_token_id=self.tokenizer.eos_token_id)
            if self.device == 'cuda':
                self.torch.cuda.synchronize()
            tokens = output[0][count:]
            text = self.tokenizer.decode(tokens, skip_special_tokens=True)
            record.update(raw_content=text, output_tokens=len(tokens), seed=seed)
            if len(tokens) >= self.cfg.get('max_new_tokens', 1600) and int(tokens[-1]) != self.tokenizer.eos_token_id:
                raise ModelError('Output token limit reached; partial JSON not accepted')
            result = json_object(text)
            record.update(status='completed', response=result)
            return result
        except Exception as exc:
            record.update(status='failed', error_type=type(exc).__name__, error=str(exc))
            raise
        finally:
            record['seconds'] = time.perf_counter() - start


class RepairModel:
    """One format-repair retry. Never supplies a scripted semantic response."""
    def __init__(self, model):
        self.model = model
        self.model_id, self.mode = model.model_id, model.mode

    @property
    def audit(self):
        return self.model.audit

    def complete(self, stage, system, payload):
        try:
            return self.model.complete(stage, system, payload)
        except ModelError as exc:
            if 'JSON' not in str(exc):
                raise
            raw = self.model.audit[-1].get('raw_content', '')
            return self.model.complete(stage, system + '\nThe previous response was invalid JSON. Return ONLY the specified JSON object.',
                         {'original_request': payload, 'invalid_response': raw, 'error': str(exc)})
