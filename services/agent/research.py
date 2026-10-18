"""Explicit, offline research preparation. Never trains or promotes model weights."""

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import struct
from memory import redact

CONFIG_KEYS = (
    'model_type', 'architectures', 'hidden_size', 'intermediate_size',
    'num_hidden_layers', 'num_attention_heads', 'num_key_value_heads',
    'vocab_size', 'head_dim', 'rope_theta', 'rope_scaling', 'sliding_window',
    'tie_word_embeddings', 'hidden_act', 'attention_bias',
)
BENCHMARKS = [
    {'id': 'whitespace', 'prompt': 'Create whitespace.py with normalize_spaces(text) that strips edges and collapses all runs of whitespace to one ASCII space. Add Python unittest tests for empty input, tabs, newlines and repeated spaces. Use python-unittest.',
     'module': 'whitespace', 'function': 'normalize_spaces',
     'oracle': [{'input': '', 'expected': ''}, {'input': ' a  b ', 'expected': 'a b'}, {'input': '\talpha\n beta\t', 'expected': 'alpha beta'}]},
    {'id': 'stable-unique', 'prompt': 'Create stable_unique.py with stable_unique(items) that removes duplicates from a list of hashable values while preserving order. Add Python unittest tests for empty input, strings, integers and repeated values. Use python-unittest.',
     'module': 'stable_unique', 'function': 'stable_unique',
     'oracle': [{'input': [], 'expected': []}, {'input': [1, 2, 1, 3, 2], 'expected': [1, 2, 3]}, {'input': ['a', 'b', 'a'], 'expected': ['a', 'b']}]},
]


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 20_000_000:
        raise ValueError('Research JSON input is too large')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def safe_text(value):
    if not isinstance(value, str) or redact(value) != value:
        raise ValueError('Possible secret in research example; review and remove it first')
    return value


def dataset(memory, reports):
    """Match test-backed memory provenance to the exact exported task patches."""
    if not isinstance(memory, list):
        raise ValueError('A local memory export list is required')
    tasks = {report['id']: report for report in reports}
    if len(tasks) != len(reports):
        raise ValueError('Duplicate task reports')
    records, provenance = [], []
    for case in memory:
        metadata = case['metadata']
        task = tasks.get(metadata.get('task'))
        if task is None:
            continue
        phases = {event['phase'] for event in task['events']}
        if (task['state'] != 'completed' or metadata.get('source') != 'local-test-and-review'
                or metadata.get('weight_training') is not False
                or not {'test', 'independent-review', 'review'}.issubset(phases)
                or not case.get('evidence') or any(marker in str(metadata.get('model', '')).casefold()
                                                 for marker in ('test fixture', 'simulated inference'))):
            raise ValueError('Only completed, test-backed, independently reviewed cases are eligible')
        expected = [{'path': change['path'], 'sha256': hashlib.sha256(change['after'].encode()).hexdigest()}
                    for change in task['changes']]
        if expected != metadata.get('patches'):
            raise ValueError('Task patches do not match verified memory provenance')
        final = {}
        for change in task['changes']:
            name = change['path']
            relative = PurePosixPath(name)
            if (relative.is_absolute() or not relative.parts or '..' in relative.parts
                    or '\\' in name or ':' in name or '.git' in relative.parts
                    or relative.name.lower().startswith('.env')):
                raise ValueError('Unsafe or private research file path')
            final[name] = safe_text(change['after'])
        if not final:
            raise ValueError('Research examples must contain actual file changes')
        prompt = safe_text(task['prompt'])
        if any(prompt.strip().casefold() == item['prompt'].strip().casefold() for item in BENCHMARKS):
            raise ValueError('Held-out benchmark request cannot enter the training dataset')
        records.append({'messages': [
            {'role': 'user', 'content': prompt},
            {'role': 'assistant', 'content': json.dumps({'files': [{'path': name, 'content': content} for name, content in final.items()]}, ensure_ascii=False)},
        ]})
        provenance.append({'case': case['id'], 'task': task['id'], 'model': metadata['model'],
                           'recipe': case['recipe'], 'patches': expected})
    if not records:
        raise ValueError('No eligible matched reviewed examples')
    return records, provenance


def checkpoint(directory, require_weights=False):
    root = Path(directory).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('A local Hugging Face checkpoint directory is required; GGUF is not trainable input')
    config = read_json(root / 'config.json')
    if config.get('quantization_config'):
        raise ValueError('Quantized checkpoints are not supported by this preparation workflow')
    if (not isinstance(config.get('model_type'), str) or not config['model_type']
            or not isinstance(config.get('architectures'), list) or not config['architectures']
            or any(not isinstance(item, str) or not item for item in config['architectures'])):
        raise ValueError('Missing model architecture metadata')
    if any(type(config.get(key)) is not int or config[key] < 1 for key in (
            'hidden_size', 'intermediate_size', 'num_hidden_layers', 'num_attention_heads', 'vocab_size')):
        raise ValueError('Missing positive model dimension metadata')
    tokenizer = {name: digest(root / name) for name in ('tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json', 'added_tokens.json') if (root / name).is_file()}
    if 'tokenizer.json' not in tokenizer:
        raise ValueError('A local tokenizer.json is required')
    files = sorted(root.glob('*.safetensors'))
    if require_weights and not files:
        raise ValueError('Floating-point safetensors checkpoints are required for merge validation')
    shapes, hashes = {}, {}
    for path in files:
        ranges = []
        with path.open('rb') as source:
            length_bytes = source.read(8)
            if len(length_bytes) != 8:
                raise ValueError('Truncated safetensors header')
            length = struct.unpack('<Q', length_bytes)[0]
            if not 2 <= length <= 32_000_000:
                raise ValueError('Unsupported safetensors header size')
            header = json.loads(source.read(length))
        for name, tensor in header.items():
            if name == '__metadata__':
                continue
            size = {'F16': 2, 'BF16': 2, 'F32': 4, 'F64': 8}.get(tensor['dtype'])
            shape, offsets = tensor['shape'], tensor['data_offsets']
            if (not size or not isinstance(shape, list) or any(type(item) is not int or item < 0 for item in shape)
                    or not isinstance(offsets, list) or len(offsets) != 2 or any(type(item) is not int for item in offsets)
                    or not 0 <= offsets[0] <= offsets[1] <= path.stat().st_size - 8 - length
                    or offsets[1] - offsets[0] != math.prod(shape) * size or name in shapes):
                raise ValueError('Unsupported or invalid floating-point tensor layout')
            shapes[name] = shape
            ranges.append(offsets)
        ordered = sorted(ranges)
        if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
            raise ValueError('Overlapping safetensors data offsets')
        hashes[path.name] = digest(path)
    if require_weights and not shapes:
        raise ValueError('Checkpoint contains no floating-point tensors')
    return {'path': str(root), 'config': {key: config.get(key) for key in CONFIG_KEYS},
            'tokenizer': tokenizer, 'shapes': shapes, 'weights': hashes,
            'config_sha256': digest(root / 'config.json')}


def write_outputs(output, files):
    output = Path(output)
    # Never overwrite an existing research directory or any original weights.
    output.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        (output / name).write_text(content, encoding='utf-8', newline='\n')


def prepare(memory_path, reports, base, output, approved=False):
    if not approved:
        raise ValueError('Explicit --approve-export is required after reviewing source rights and privacy')
    records, provenance = dataset(read_json(memory_path), [read_json(path) for path in reports])
    model = checkpoint(base)
    if model['config']['model_type'] not in {'qwen2', 'llama', 'mistral'}:
        raise ValueError('LoRA target modules have not been validated for this architecture')
    out = Path(output).resolve()
    config = {'base_model': model['path'], 'adapter': 'lora', 'lora_r': 8, 'lora_alpha': 16,
              'lora_dropout': 0.05, 'lora_target_modules': ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
              'datasets': [{'path': str(out / 'dataset.jsonl'), 'type': 'chat_template', 'field_messages': 'messages'}],
              'val_set_size': 0.1, 'sequence_len': 2048, 'micro_batch_size': 1,
              'gradient_accumulation_steps': 8, 'num_epochs': 1, 'learning_rate': 0.0002,
              'bf16': 'auto', 'gradient_checkpointing': True, 'save_safetensors': True,
              'output_dir': str(out / 'adapter-output')}
    manifest = {'status': 'experimental-preparation-only', 'examples': len(records),
                'training_executed': False, 'weights_modified': False, 'promotion_allowed': False,
                'hardware_validated': False, 'trainer_integration_validated': False,
                'minimum_recommended_reviewed_examples': 20, 'checkpoint': model,
                'provenance': provenance, 'held_out_results': None,
                'limitations': ['Secret filters are incomplete; human privacy and rights review is mandatory.',
                                'The bundled GGUF cannot be used for parameter training.',
                                'CPU/16 GB baseline is unsupported for training; optional GPU tools are not bundled.']}
    write_outputs(out, {'dataset.jsonl': ''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records),
                        'lora-config.yml': json.dumps(config, indent=2) + '\n',
                        'benchmarks.json': json.dumps({'cases': BENCHMARKS, 'results': None, 'promotion_allowed': False}, indent=2),
                        'preparation.json': json.dumps(manifest, indent=2)})
    return manifest


def prepare_merge(directories, output):
    if len(directories) < 2:
        raise ValueError('At least two local checkpoints are required')
    models = [checkpoint(path, require_weights=True) for path in directories]
    reference = models[0]
    for candidate in models[1:]:
        if any(candidate[key] != reference[key] for key in ('config', 'tokenizer', 'shapes')):
            raise ValueError('Checkpoint architecture, tokenizer or tensor shapes are incompatible')
    config = {'merge_method': 'linear', 'dtype': 'float16',
              'models': [{'model': model['path'], 'parameters': {'weight': 1 / len(models)}} for model in models]}
    manifest = {'status': 'experimental-compatible-inputs-only', 'merge_executed': False,
                'weights_modified': False, 'promotion_allowed': False, 'models': models,
                'held_out_results': None, 'mergekit_integration_validated': False}
    write_outputs(output, {'mergekit.yml': json.dumps(config, indent=2),
                           'merge-preparation.json': json.dumps(manifest, indent=2),
                           'benchmarks.json': json.dumps({'cases': BENCHMARKS, 'results': None, 'promotion_allowed': False}, indent=2)})
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('prepare')
    export.add_argument('--memory-export', required=True)
    export.add_argument('--report', action='append', required=True)
    export.add_argument('--base-checkpoint', required=True)
    export.add_argument('--output', required=True)
    export.add_argument('--approve-export', action='store_true')
    merge = commands.add_parser('prepare-merge')
    merge.add_argument('--checkpoint', action='append', required=True)
    merge.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        result = prepare(args.memory_export, args.report, args.base_checkpoint, args.output, args.approve_export)
    else:
        result = prepare_merge(args.checkpoint, args.output)
    print(json.dumps({'status': result['status'], 'promotion_allowed': False}, indent=2))


if __name__ == '__main__':
    main()
