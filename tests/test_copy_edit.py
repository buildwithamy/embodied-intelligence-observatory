"""Review provenance must remain bound to the actual publication inputs."""
import pytest

from embodied_observatory.edition import copy_edit_provenance
from embodied_observatory.pipeline import write_json
from scripts.deepseek_polish import validate_edits


def record(root, **updates):
    payload = {'week': '2026-W40', 'status': 'reviewed_applied', 'issue_sha256': 'issue-digest',
               'candidates_sha256': 'paper-digest', 'provider': 'DeepSeek', 'model': 'fixture-model',
               'calls': 8, 'usage': {'total_tokens': 10}, 'private_extra': 'must not be copied'}
    payload.update(updates)
    write_json(root / 'runs/2026-W40-deepseek-polish.json', payload)


def test_only_reviewed_matching_inputs_get_model_attribution(tmp_path):
    record(tmp_path)
    result = copy_edit_provenance(tmp_path, '2026-W40', 'issue-digest', 'paper-digest')
    assert result['calls'] == 8 and result['model'] == 'fixture-model'
    assert 'private_extra' not in result
    record(tmp_path, status='awaiting_semantic_review')
    assert copy_edit_provenance(tmp_path, '2026-W40', 'issue-digest', 'paper-digest') is None


@pytest.mark.parametrize('issue,papers', [('changed-issue', 'paper-digest'), ('issue-digest', 'changed-papers')])
def test_changed_copy_cannot_reuse_an_old_review(tmp_path, issue, papers):
    record(tmp_path)
    with pytest.raises(ValueError, match='does not match'):
        copy_edit_provenance(tmp_path, '2026-W40', issue, papers)


@pytest.mark.parametrize('edits', [[], [{'path': 'forbidden', 'revised': 'text'}],
                                 [{'path': 'allowed', 'revised': ''}]])
def test_model_cannot_omit_expand_or_empty_the_requested_fields(edits):
    with pytest.raises(ValueError):
        validate_edits({'allowed_fields': [{'path': 'allowed', 'text': 'original'}]}, {'edits': edits})
