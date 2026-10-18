"""Research preparation fixtures are not trained models or real inference evidence."""

import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/agent'))
import research


class ResearchPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.model('base')
        self.report = {'id': 'fixture-task', 'state': 'completed', 'prompt': 'Create a local greeting function',
                       'events': [{'phase': phase} for phase in ('test', 'independent-review', 'review')],
                       'changes': [{'path': 'hello.py', 'after': 'def hello(): return "hello"\n'}]}
        patches = [{'path': item['path'], 'sha256': hashlib.sha256(item['after'].encode()).hexdigest()} for item in self.report['changes']]
        self.memory = [{'id': 'fixture-case', 'recipe': 'python-unittest', 'evidence': 'fixture test evidence',
                        'metadata': {'source': 'local-test-and-review', 'task': self.report['id'],
                                     'model': 'unit-test metadata fixture', 'patches': patches, 'weight_training': False}}]
        self.report_path = self.root / 'report.json'
        self.memory_path = self.root / 'memory.json'
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.report_path.write_text(json.dumps(self.report))
        self.memory_path.write_text(json.dumps(self.memory))

    def model(self, name, shape=1, tokenizer='fixture-tokenizer'):
        directory = self.root / name
        directory.mkdir()
        config = {'model_type': 'qwen2', 'architectures': ['FixtureForCausalLM'],
                  'hidden_size': 1, 'intermediate_size': 1, 'num_hidden_layers': 1,
                  'num_attention_heads': 1, 'vocab_size': 1}
        (directory / 'config.json').write_text(json.dumps(config))
        (directory / 'tokenizer.json').write_text(json.dumps({'fixture': tokenizer}))
        header = json.dumps({'fixture.weight': {'dtype': 'F32', 'shape': [shape], 'data_offsets': [0, 4 * shape]}}).encode()
        (directory / 'model.safetensors').write_bytes(struct.pack('<Q', len(header)) + header + b'\0' * (4 * shape))
        return directory

    def prepare(self, approved=True):
        return research.prepare(self.memory_path, [self.report_path], self.base, self.root / 'output', approved)

    def test_reviewed_export_preserves_weights_and_never_claims_training(self):
        before = research.digest(self.base / 'model.safetensors')
        result = self.prepare()
        self.assertFalse(result['training_executed'])
        self.assertFalse(result['promotion_allowed'])
        self.assertFalse(result['hardware_validated'])
        self.assertEqual(before, research.digest(self.base / 'model.safetensors'))
        record = json.loads((self.root / 'output/dataset.jsonl').read_text())
        self.assertEqual(record['messages'][0]['role'], 'user')
        self.assertTrue((self.root / 'output/lora-config.yml').is_file())

    def test_export_requires_explicit_approval(self):
        with self.assertRaisesRegex(ValueError, 'approve-export'):
            self.prepare(False)
        self.assertFalse((self.root / 'output').exists())

    def test_tampered_or_failed_reports_are_rejected(self):
        self.report['changes'][0]['after'] += '# changed after review'
        self.save()
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.prepare()
        self.report['state'] = 'failed'
        self.save()
        with self.assertRaisesRegex(ValueError, 'completed'):
            self.prepare()
        self.assertFalse((self.root / 'output').exists())

    def test_secret_and_existing_output_are_protected(self):
        self.report['prompt'] = 'Use api_key="private-value"'
        self.save()
        with self.assertRaisesRegex(ValueError, 'secret'):
            self.prepare()
        self.report['prompt'] = 'Safe request'
        self.save()
        (self.root / 'output').mkdir()
        (self.root / 'output/keep.txt').write_text('keep')
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual((self.root / 'output/keep.txt').read_text(), 'keep')

    def test_compatible_merge_is_only_preparation(self):
        second = self.model('second')
        result = research.prepare_merge([self.base, second], self.root / 'merge')
        self.assertFalse(result['merge_executed'])
        self.assertFalse(result['promotion_allowed'])
        self.assertEqual(json.loads((self.root / 'merge/mergekit.yml').read_text())['merge_method'], 'linear')

    def test_merge_rejects_tensor_or_tokenizer_mismatch(self):
        second = self.model('different-shape', shape=2)
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            research.prepare_merge([self.base, second], self.root / 'merge')
        third = self.model('different-tokenizer', tokenizer='different')
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            research.prepare_merge([self.base, third], self.root / 'merge')

    def test_merge_rejects_truncated_or_quantized_input(self):
        (self.base / 'model.safetensors').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            research.checkpoint(self.base, True)
        config = json.loads((self.base / 'config.json').read_text())
        config['quantization_config'] = {'bits': 4}
        (self.base / 'config.json').write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'Quantized'):
            research.checkpoint(self.base)

    def test_merge_rejects_overlapping_tensor_data(self):
        tensor = {'dtype': 'F32', 'shape': [1], 'data_offsets': [0, 4]}
        header = json.dumps({'one': tensor, 'two': tensor}).encode()
        (self.base / 'model.safetensors').write_bytes(struct.pack('<Q', len(header)) + header + b'\0' * 4)
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            research.checkpoint(self.base, True)


if __name__ == '__main__':
    unittest.main()
