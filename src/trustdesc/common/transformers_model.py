"""Optional lower-compute experiment; not one of the paper's model settings.

No imports/downloads until explicitly constructed with allow_download=True.
GPU inference has not been executed in the local Mac session.
"""
from __future__ import annotations

import json
import re
import time

from .io import canonical, digest, ValidationError
from .models import ModelError


def parse_json_response(text):
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelError('Model did not return strict JSON; inspect locally saved raw output') from exc
    if not isinstance(result, dict):
        raise ValidationError('Model JSON must be an object')
    return result


class TransformersModel:
    mode = 'experimental_small_model_inference'

    def __init__(self, *, allow_download=False, revision='2e1fd39', seed=42,
                 max_input_tokens=4096, max_new_tokens=2048):
        if not allow_download:
            raise ModelError('Public model download requires explicit opt-in')
        if not re.fullmatch(r'[0-9a-f]{7,40}', revision):
            raise ModelError('A fixed model commit revision is required')
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if not torch.cuda.is_available():
            raise ModelError('Optional experiment requires a CUDA GPU; run the CPU fixture track instead')
        self.torch = torch
        self.model_id = 'Qwen/Qwen2.5-Coder-1.5B-Instruct'
        self.revision, self.seed = revision, seed
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=revision,
                                                        trust_remote_code=False, token=False)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_id, revision=revision,
                                                         trust_remote_code=False, token=False,
                                                         use_safetensors=True, torch_dtype=torch.float16,
                                                         attn_implementation='eager').to('cuda').eval()
        self.max_input_tokens, self.max_new_tokens = max_input_tokens, max_new_tokens
        self.audit = []
        self.runtime = {'torch': torch.__version__, 'transformers': transformers.__version__,
                        'GPU': torch.cuda.get_device_name(0), 'revision_requested': revision,
                        'resolved_commit': getattr(self.model.config, '_commit_hash', None),
                        'precision': 'float16', 'attention': 'eager'}

    def complete(self, stage, system, payload):
        messages = [{'role':'system','content':system},{'role':'user','content':canonical(payload)}]
        inputs = self.tokenizer.apply_chat_template(messages, tokenize=True,
                   add_generation_prompt=True, return_dict=True, return_tensors='pt').to('cuda')
        n = inputs['input_ids'].shape[-1]
        if n > self.max_input_tokens:
            raise ModelError('Input exceeds configured context cap; no silent truncation')
        self.torch.manual_seed(self.seed)
        self.torch.cuda.synchronize()
        start = time.perf_counter()
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, do_sample=True, temperature=0.2,
                         max_new_tokens=self.max_new_tokens, pad_token_id=self.tokenizer.eos_token_id)
        self.torch.cuda.synchronize()
        tokens = output[0][n:]
        text = self.tokenizer.decode(tokens, skip_special_tokens=True)
        record = {'stage':stage,'messages':messages,'request_hash':digest(messages),'raw_content':text,
                  'model':self.model_id,'mode':self.mode,'runtime':self.runtime,'seed':self.seed,
                  'input_tokens':n,'output_tokens':len(tokens),'seconds':time.perf_counter()-start,
                  'cost_usd':None,'max_gpu_allocated_bytes':self.torch.cuda.max_memory_allocated()}
        self.audit.append(record)
        if len(tokens) >= self.max_new_tokens and int(tokens[-1]) != self.tokenizer.eos_token_id:
            raise ModelError('Generation hit token limit; no silent partial response')
        result = parse_json_response(text)
        record['response'] = result
        return result
