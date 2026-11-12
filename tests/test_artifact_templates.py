import json
import tempfile
import unittest
from pathlib import Path
from kgmaker.artifact_templates import render
from kgmaker.analysis_model import AnalysisError


class ArtifactTemplateTests(unittest.TestCase):
    def test_defaults_and_literal_values(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            value = render(root, 'requirement', {'title': 'Request', 'body': '$(touch unsafe)'})
            self.assertIn('$(touch unsafe)', value['text'])
            self.assertEqual([], list(root.iterdir()))
            self.assertEqual(value, render(root, 'requirement', {'title': 'Request', 'body': '$(touch unsafe)'}))

    def test_custom_template_and_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            target = root / '.kgmaker/templates'
            target.mkdir(parents=True)
            manifest = dict(schema_version=1, id='custom', kind='analysis', revision=1,
                            description='Example', variables=['body'], content='body.md')
            (target / 'custom.json').write_text(json.dumps(manifest))
            (target / 'body.md').write_text('Analysis: ${body}')
            first = render(root, 'analysis', {'body': 'Evidence'}, 'custom')
            self.assertEqual('Analysis: Evidence', first['text'])
            (target / 'body.md').write_text('Changed: ${body}')
            self.assertNotEqual(first['template']['sha256'], render(root, 'analysis', {'body': 'Evidence'}, 'custom')['template']['sha256'])
            manifest['content'] = '../outside.md'
            (target / 'custom.json').write_text(json.dumps(manifest))
            with self.assertRaises(AnalysisError):
                render(root, 'analysis', {'body': 'Evidence'}, 'custom')

    def test_invalid_selection_and_filename(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(AnalysisError):
                render(root, 'analysis', {}, 'missing')
            for slug in ('../escape', 'bad:name', 'bad/name'):
                with self.subTest(slug=slug), self.assertRaises(AnalysisError):
                    render(root, 'filename', {'id': '', 'slug': slug, 'extension': 'md'})

    def test_install_preserves_edits_and_generation_tracks_provenance(self):
        from kgmaker.artifact_templates import install, generate
        from kgmaker.provenance import trace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            install(root)
            path=root/'.kgmaker/templates/requirement.txt'
            path.write_text('Request: ${title}\n${body}')
            install(root)
            self.assertTrue(path.read_text().startswith('Request:'))
            result=generate(root,'requirement',{'title':'Test','body':'Expected outcome'},
                            output_dir='requirements',filename='request.md')
            self.assertIn('Request: Test',(root/'requirements/request.md').read_text())
            report=trace(root,result['reference'])
            self.assertEqual(result['template'],report['references'][0]['payload']['template'])
            with self.assertRaises(AnalysisError):
                generate(root,'requirement',{'title':'Overwrite','body':'No'},output_dir='requirements',filename='request.md')

    def test_defaults_selection_and_symlink_escape(self):
        from kgmaker.artifact_templates import install
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);install(root)
            folder=root/'.kgmaker/templates'
            (folder/'defaults.json').write_text(json.dumps({'analysis':'missing'}))
            with self.assertRaises(AnalysisError):render(root,'analysis',{'title':'T','body':'B'})
            (folder/'defaults.json').unlink()
            (folder/'analysis.txt').unlink()
            try:(folder/'analysis.txt').symlink_to(root/'outside.txt')
            except OSError:self.skipTest('symlinks unavailable')
            with self.assertRaises(AnalysisError):render(root,'analysis',{'title':'T','body':'B'})

    def test_generate_rejects_noncanonical_and_reserved_exports_without_mutation(self):
        from kgmaker.artifact_templates import generate
        invalid_directories = (
            '.git', '.Git', '.github', '.kgmaker', './out', 'out/', 'out//nested',
            'out/.Git/nested', 'CON .txt',
        )
        invalid_filenames = ('.git', '.Github', '.kgmaker', 'CON .txt')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for output_dir in invalid_directories:
                with self.subTest(output_dir=output_dir), self.assertRaises(AnalysisError):
                    generate(root, 'requirement', {'title': 'T', 'body': 'B'},
                             output_dir=output_dir, filename='safe.md')
            for filename in invalid_filenames:
                with self.subTest(filename=filename), self.assertRaises(AnalysisError):
                    generate(root, 'requirement', {'title': 'T', 'body': 'B'},
                             output_dir='out', filename=filename)
            self.assertEqual([], list(root.iterdir()))

    def test_install_preflights_all_pairs_before_writing(self):
        from kgmaker.artifact_templates import install
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / '.kgmaker/templates'
            folder.mkdir(parents=True)
            blocked = folder / 'requirement.json'
            try:
                blocked.symlink_to(root / 'outside.json')
            except OSError:
                self.skipTest('symlinks unavailable')
            with self.assertRaises(AnalysisError):
                install(root)
            self.assertEqual({'requirement.json'}, {path.name for path in folder.iterdir()})
            self.assertFalse((root / 'outside.json').exists())

    def test_install_rolls_back_a_late_write_failure(self):
        from unittest import mock
        from kgmaker.artifact_templates import install
        original_open = Path.open

        def fail_on_requirement(path, *args, **kwargs):
            if path.name == 'requirement.json' and args and args[0] == 'x':
                raise OSError('injected late write failure')
            return original_open(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with mock.patch.object(Path, 'open', fail_on_requirement):
                with self.assertRaisesRegex(OSError, 'injected late write failure'):
                    install(root)
            self.assertEqual([], list(root.iterdir()))
