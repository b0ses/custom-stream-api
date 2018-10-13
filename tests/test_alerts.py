from custom_stream_api.alerts import alerts


def test_clean_name():
    assert alerts.clean_name(' test') == 'test'
    assert alerts.clean_name('test name') == 'test_name'
    assert alerts.clean_name('Test Name') == 'test_name'


def test_add_remove_list_alerts(test_app):
    with test_app.app_context():
        # Testing add alerts
        alerts.add_alert(message='Test Message 1', sound='Test Sound 1')
        alerts.add_alert(message='Test Message 2', sound='Test Sound 2')
        alerts.add_alert(message='Test Message 3', sound='Test Sound 3')

        # Testing list alert
        all_alerts = [alert.as_dict() for alert in alerts.list_alerts()]
        assert len(all_alerts) == 3
        expected_alerts = [1, 2, 3]
        current_index = 0
        for alert in all_alerts:
            expected_alert_num = expected_alerts[current_index]
            assert alert == {
                'name': 'test_message_{}'.format(expected_alert_num),
                'text': 'Test Message {}'.format(expected_alert_num),
                'sound': 'Test Sound {}'.format(expected_alert_num),
                'image': None
            }
            current_index += 1

        # Testing remove alert
        alerts.remove_alert('test_message_2')

        all_alerts = [alert.as_dict() for alert in alerts.list_alerts()]
        assert len(all_alerts) == 2
        expected_alerts = [1, 3]
        current_index = 0
        for alert in all_alerts:
            expected_alert_num = expected_alerts[current_index]
            assert alert == {
                'name': 'test_message_{}'.format(expected_alert_num),
                'text': 'Test Message {}'.format(expected_alert_num),
                'sound': 'Test Sound {}'.format(expected_alert_num),
                'image': None
            }
            current_index += 1
