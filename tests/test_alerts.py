import pytest

from custom_stream_api.alerts import alerts
from custom_stream_api.counts import counts

IMPORT_ALERTS = [
    {
        'name': 'test_text_1',
        'text': 'Test Text 1',
        'sound': 'http://www.test.com/test_sound_1.mp3',
        'duration': 3000,
        'image': '',
        'thumbnail': '',
        'effect': ''
    },
    {
        'name': 'test_text_2',
        'text': 'Test Text 2',
        'sound': 'http://www.test.com/test_sound_2.mp3',
        'duration': 3000,
        'image': '',
        'thumbnail': '',
        'effect': ''
    },
    {
        'name': 'test_text_3',
        'text': 'Test Text 3',
        'sound': 'http://www.test.com/test_sound_3.mp3',
        'duration': 3000,
        'image': '',
        'thumbnail': '',
        'effect': ''
    }
]

IMPORT_GROUP_ALERTS = [
    {
        'name': 'first_two',
        'alerts': [
            'test_text_1',
            'test_text_2'
        ],
        'thumbnail': None,
        'chat_message': None,
        'always_chat': False
    },
    {
        'name': 'last_two',
        'alerts': [
            'test_text_2',
            'test_text_3'
        ],
        'thumbnail': None,
        'chat_message': 'last two!',
        'always_chat': True
    }
]

COUNTS_IMPORT = [
    {
        'name': 'count1',
        'count': 37,
        'group_name': 'first_two',
    },
    {
        'name': 'count2',
        'count': 2,
        'group_name': 'first_two',
    }
]


@pytest.fixture
def import_counts(app):
    counts.import_counts(COUNTS_IMPORT)


@pytest.fixture
def import_alerts(app):
    alerts.import_alerts(IMPORT_ALERTS)


@pytest.fixture
def import_groups(import_alerts):
    alerts.import_groups(IMPORT_GROUP_ALERTS)


def test_validate_sound():
    # Allow blank sounds
    assert alerts.validate_sound() is None
    assert alerts.validate_sound('') is None

    # Success tests
    test_mp3 = 'http://www.test.com/test_mp3.mp3'
    test_wav = 'http://www.test.com/some/random/dir/test_wav.wav'
    assert alerts.validate_sound(test_mp3) == 'test_mp3'
    assert alerts.validate_sound(test_wav) == 'test_wav'

    # Fail tests
    wrong_extension_1 = 'http://www.test.com/test_mp3.blah'
    wrong_extension_2 = 'http://www.test.com/test_mp3.mp3s'
    wrong_url_1 = 'htp://www.test.com/test_mp3.mp3'
    wrong_url_2 = 'htp://test_mp3.mp3'
    wrong_url_3 = 'htp://www./test_mp3.mp3'
    for fail_test_sound in [wrong_extension_1, wrong_extension_2, wrong_url_1, wrong_url_2, wrong_url_3]:
        validated_sound = None
        try:
            validated_sound = alerts.validate_sound(fail_test_sound)
        except Exception:
            assert True
        assert validated_sound is None


def test_validate_effect():
    # Allow blank effects
    assert alerts.validate_effect('') == ''

    # Success tests
    for effect in alerts.VALID_EFFECTS:
        assert alerts.validate_effect(effect) == effect

    # Fail tests
    non_existent_effect = 'blahhhhh'
    validated_effect = None
    try:
        validated_effect = alerts.validate_effect(non_existent_effect)
    except Exception:
        assert True
    assert validated_effect is None


def test_validate_duration():
    # Success tests
    assert alerts.validate_duration(1) == 1
    assert alerts.validate_duration('2') == 2

    # Fail tests
    for bad_duration in ['', -3000, '1.2']:
        validated_duration = None
        try:
            validated_duration = alerts.validate_duration(bad_duration)
        except Exception:
            assert True
        assert validated_duration is None


def test_validate_image():
    # Allow blank sounds
    assert alerts.validate_image() is None
    assert alerts.validate_image('') is None

    # Success tests
    test_gif = 'http://www.test.com/test_gif.gif'
    test_png = 'http://www.test.com/some/random/dir/test_png.png'
    assert alerts.validate_image(test_gif) == 'test_gif'
    assert alerts.validate_image(test_png) == 'test_png'

    # Fail tests
    wrong_extension_1 = 'http://www.test.com/test_gif.blah'
    wrong_extension_2 = 'http://www.test.com/test_gif.gifs'
    wrong_url_1 = 'htp://www.test.com/test_gif.gif'
    wrong_url_2 = 'htp://test_gif.gif'
    wrong_url_3 = 'htp://www./test_gif.gif'
    for fail_test_image in [wrong_extension_1, wrong_extension_2, wrong_url_1, wrong_url_2, wrong_url_3]:
        validated_image = None
        try:
            validated_image = alerts.validate_image(fail_test_image)
        except Exception:
            assert True
        assert validated_image is None


def test_validate_hex_color():
    # Valid cases
    assert alerts.validate_color_hex('#DDD') == '#DDD'
    assert alerts.validate_color_hex('#111111') == '#111111'

    # Invalid cases
    invalid_cases = ['DDD', '#', '#1', '#11', '#1111', '#11111', '#GGGGGG']
    for case in invalid_cases:
        hex = None
        try:
            hex = alerts.validate_color_hex(case)
        except Exception:
            assert True
        assert hex is None


def test_generate_name():
    # Testg cleaning up the string
    assert alerts.generate_name(name=' test') == 'test'
    assert alerts.generate_name(name='test name') == 'test_name'
    assert alerts.generate_name(name='Test Name') == 'test_name'

    # Tests getting the name from the text
    assert alerts.generate_name(text='test text') == 'test_text'

    # Tests getting the name from the text
    test_sound = 'http://www.test.com/test_sound.mp3'
    assert alerts.generate_name(sound=test_sound) == 'test_sound'


def test_import_export_alerts(import_alerts):
    assert alerts.list_alerts()[0] == IMPORT_ALERTS


def test_filter_alerts(import_alerts):
    assert alerts.list_alerts(limit=1)[0][0] == IMPORT_ALERTS[0]
    assert alerts.list_alerts(limit=1, page=2)[0][0] == IMPORT_ALERTS[1]
    assert alerts.list_alerts(limit=2, page=2)[0][0] == IMPORT_ALERTS[2]

    assert alerts.list_alerts(sort='-name')[0][0] == IMPORT_ALERTS[2]

    assert alerts.list_alerts(search='2')[0][0] == IMPORT_ALERTS[1]


def test_remove_alert(import_groups):
    alerts.remove_alert('test_text_2')
    all_alerts = [alert['name'] for alert in alerts.list_alerts()[0]]
    assert 'test_text_2' not in all_alerts

    first_two_group_alerts = [group for group in alerts.list_groups()[0] if group['name'] == 'first_two'][0]['alerts']
    assert 'test_text_2' not in first_two_group_alerts


def test_import_export_groups(import_groups):
    assert alerts.list_groups()[0] == IMPORT_GROUP_ALERTS


def test_filter_group_alerts(import_alerts, import_groups):
    assert alerts.list_groups(limit=1)[0][0] == IMPORT_GROUP_ALERTS[0]
    assert alerts.list_groups(limit=1, page=2)[0][0] == IMPORT_GROUP_ALERTS[1]
    assert alerts.list_groups(limit=2, page=1)[0][1] == IMPORT_GROUP_ALERTS[1]

    assert alerts.list_groups(sort='-name')[0][0] == IMPORT_GROUP_ALERTS[1]

    assert alerts.list_groups(search='last')[0][0] == IMPORT_GROUP_ALERTS[1]


def test_alert(import_alerts):
    expected = 'Test Text 1'
    assert alerts.alert('test_text_1', hit_socket=False) == expected


def test_group_alert(import_groups, import_counts):
    expected = ['Test Text 2', 'Test Text 3']
    assert alerts.group_alert('last_two', hit_socket=False) in expected

    expected = ['Test Text 1', 'Test Text 2']
    assert alerts.group_alert('first_two', hit_socket=False) in expected

    expected = ['Test Text 1', 'Test Text 2']
    assert alerts.group_alert('first_two', hit_socket=False) in expected

    count = counts.get_count('count1')
    assert count == 39

    count = counts.get_count('count2')
    assert count == 4


def test_remove_from_group(import_groups):
    alerts.remove_from_group('first_two', ['test_text_2'])
    group_alerts = [group for group in alerts.list_groups()[0] if group['name'] == 'first_two'][0]['alerts']
    expected = ['test_text_1']
    assert expected == group_alerts


def test_remove_group(import_groups):
    alerts.remove_group('last_two')
    assert 'last_two' not in alerts.list_groups()[0]
