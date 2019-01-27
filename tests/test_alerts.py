from custom_stream_api.alerts import alerts


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


def test_alerts(app):
    # Testing add alerts
    test_sound_1 = 'http://www.test.com/test_sound_1.mp3'
    alerts.add_alert(text='Test Text 1', sound=test_sound_1)
    test_sound_2 = 'http://www.test.com/test_sound_2.mp3'
    alerts.add_alert(text='Test Text 2', sound=test_sound_2)
    test_sound_3 = 'http://www.test.com/test_sound_3.mp3'
    alerts.add_alert(text='Test Text 3', sound=test_sound_3)

    # Testing list alert
    all_alerts = [alert.as_dict() for alert in alerts.list_alerts()]
    assert len(all_alerts) == 3
    expected_alerts = [1, 2, 3]
    current_index = 0
    for alert in all_alerts:
        expected_alert_num = expected_alerts[current_index]
        assert alert == {
            'name': 'test_text_{}'.format(expected_alert_num),
            'text': 'Test Text {}'.format(expected_alert_num),
            'sound': 'http://www.test.com/test_sound_{}.mp3'.format(expected_alert_num),
            'image': '',
            'duration': 3000,
            'effect': '',
            'thumbnail': ''
        }
        current_index += 1

    # Testing remove alert
    alerts.remove_alert('test_text_2')

    all_alerts = [alert.as_dict() for alert in alerts.list_alerts()]
    assert len(all_alerts) == 2
    expected_alerts = [1, 3]
    current_index = 0
    for alert in all_alerts:
        expected_alert_num = expected_alerts[current_index]
        assert alert == {
            'name': 'test_text_{}'.format(expected_alert_num),
            'text': 'Test Text {}'.format(expected_alert_num),
            'sound': 'http://www.test.com/test_sound_{}.mp3'.format(expected_alert_num),
            'image': '',
            'duration': 3000,
            'effect': '',
            'thumbnail': ''
        }
        current_index += 1


def test_group_alerts(app):
    test_sound_1 = 'http://www.test.com/test_sound_1.mp3'
    test_sound_2 = 'http://www.test.com/test_sound_2.mp3'
    test_sound_3 = 'http://www.test.com/test_sound_3.mp3'
    alerts.add_alert(text='Test Text 1', sound=test_sound_1)
    alerts.add_alert(text='Test Text 2', sound=test_sound_2)
    alerts.add_alert(text='Test Text 3', sound=test_sound_3)

    # Testing add to group
    alerts.add_to_group('first_two', ['test_text_1', 'test_text_2'])
    alerts.add_to_group('last_two', ['test_text_2', 'test_text_3'])

    # Testing list groups
    all_groups = alerts.list_groups()
    expected_groups = [
        {
            'name': 'first_two',
            'alerts': [
                'test_text_1',
                'test_text_2'
            ]
        },
        {
            'name': 'last_two',
            'alerts': [
                'test_text_2',
                'test_text_3'
            ]
        }
    ]
    assert all_groups == expected_groups

    # Testing remove from group
    alerts.remove_from_group('first_two', ['test_text_2'])
    group_alerts = [group for group in alerts.list_groups() if group['name'] == 'first_two'][0]['alerts']
    expected = ['test_text_1']
    assert expected == group_alerts

    # Testing remove whole group
    alerts.remove_group('last_two')
    assert 'last_two' not in alerts.list_groups()
