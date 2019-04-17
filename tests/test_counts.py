import pytest

from custom_stream_api.counts import counts

COUNTS_IMPORT = [
    {
        'name': 'count1',
        'count': -10,
        'group_name': None
    },
    {
        'name': 'count2',
        'count': 20,
        'group_name': None
    },
    {
        'name': 'count3',
        'count': 90,
        'group_name': None
    }
]


@pytest.fixture
def import_counts(app):
    counts.import_counts(COUNTS_IMPORT)


def test_export_counts(import_counts):
    assert counts.list_counts() == COUNTS_IMPORT


def test_get_count(import_counts):
    assert counts.get_count('count2') == 20


def test_add_to_count(import_counts):
    assert counts.add_to_count('count1') == -9


def test_subtract_from_count(import_counts):
    assert counts.subtract_from_count('count3') == 89


def test_reset_count(import_counts):
    assert counts.reset_count('count2') == 0


def test_set_count(import_counts):
    assert counts.set_count('count3', 943) == 943


def test_remove_count(import_counts):
    counts.remove_count('count1')
    assert 'count1' not in counts.list_counts()
