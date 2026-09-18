import json
import unittest

from modular_cli.service.decorators import (
    ERROR_STATUS,
    JSON_VIEW,
    SUCCESS_STATUS,
    CommandResponse,
    ResponseFormatter,
    _split_operation_status,
)


class SplitOperationStatusTests(unittest.TestCase):
    def test_domain_status_with_operation_wrapper(self):
        kwargs = {
            'task_id': 'iam_theory',
            'status': 'up_to_date',
            'Status': 'SUCCESS',
        }
        op_status, remaining = _split_operation_status(kwargs)
        self.assertEqual(op_status, 'SUCCESS')
        self.assertEqual(
            remaining,
            {'task_id': 'iam_theory', 'status': 'up_to_date'},
        )
        self.assertNotIn('Status', remaining)

    def test_operation_status_only(self):
        kwargs = {'task_id': 'x', 'Status': 'SUCCESS'}
        op_status, remaining = _split_operation_status(kwargs)
        self.assertEqual(op_status, 'SUCCESS')
        self.assertEqual(remaining, {'task_id': 'x'})

    def test_lowercase_operation_status_in_status_key(self):
        kwargs = {'status': 'success'}
        op_status, remaining = _split_operation_status(kwargs)
        self.assertEqual(op_status, 'success')
        self.assertEqual(remaining, {})

    def test_domain_status_without_operation_wrapper(self):
        kwargs = {'task_id': 't1', 'status': 'outdated'}
        op_status, remaining = _split_operation_status(kwargs)
        self.assertIsNone(op_status)
        self.assertEqual(remaining, {'task_id': 't1', 'status': 'outdated'})

    def test_failed_operation_status(self):
        kwargs = {'Status': 'FAILED'}
        op_status, remaining = _split_operation_status(kwargs)
        self.assertEqual(op_status, 'FAILED')
        self.assertEqual(remaining, {})

    def test_both_domain_values_kept_in_meta(self):
        kwargs = {'task_id': 't1', 'status': 'up_to_date', 'Status': 'pending'}
        op_status, remaining = _split_operation_status(kwargs)
        self.assertIsNone(op_status)
        self.assertEqual(
            remaining,
            {'task_id': 't1', 'status': 'up_to_date', 'Status': 'pending'},
        )

    def test_both_operation_values_status_key_wins(self):
        kwargs = {'task_id': 'x', 'status': 'SUCCESS', 'Status': 'SUCCESS'}
        op_status, remaining = _split_operation_status(kwargs)
        self.assertEqual(op_status, 'SUCCESS')
        self.assertEqual(remaining, {'task_id': 'x'})
        self.assertNotIn('status', remaining)
        self.assertNotIn('Status', remaining)

    def test_operation_status_in_status_key_drops_status_key(self):
        kwargs = {'status': 'SUCCESS', 'Status': 'up_to_date'}
        op_status, remaining = _split_operation_status(kwargs)
        self.assertEqual(op_status, 'SUCCESS')
        self.assertEqual(remaining, {})
        self.assertNotIn('Status', remaining)

    def test_conflicting_operation_statuses_status_key_wins(self):
        kwargs = {'status': 'SUCCESS', 'Status': 'FAILED'}
        op_status, remaining = _split_operation_status(kwargs)
        self.assertEqual(op_status, 'SUCCESS')
        self.assertEqual(remaining, {})


class CommandResponseTests(unittest.TestCase):
    def test_voiceover_preserves_domain_status_in_meta(self):
        resp = CommandResponse(
            message='Voiceover is up to date',
            task_id='iam_theory',
            status='up_to_date',
            Status='SUCCESS',
        )
        self.assertEqual(resp.status, 'SUCCESS')
        self.assertEqual(
            resp.meta,
            {'task_id': 'iam_theory', 'status': 'up_to_date'},
        )

    def test_both_domain_values_preserved_in_meta(self):
        resp = CommandResponse(
            message='OK',
            task_id='t1',
            status='up_to_date',
            Status='pending',
        )
        self.assertIsNone(resp.status)
        self.assertEqual(
            resp.meta,
            {
                'task_id': 't1',
                'status': 'up_to_date',
                'Status': 'pending',
            },
        )

    def test_both_operation_values_leave_meta_clean(self):
        resp = CommandResponse(
            message='OK',
            task_id='x',
            status='SUCCESS',
            Status='SUCCESS',
        )
        self.assertEqual(resp.status, 'SUCCESS')
        self.assertEqual(resp.meta, {'task_id': 'x'})

    def test_server_response_skips_validation_warning(self):
        resp = CommandResponse(message='OK', Status='SUCCESS')
        self.assertNotIn(
            'Please provide "table_title" and "items" or "message" parameter',
            resp.warnings,
        )

    def test_client_response_without_message_gets_validation_warning(self):
        resp = CommandResponse()
        self.assertIn(
            'Please provide "table_title" and "items" or "message" parameter',
            resp.warnings,
        )


class CommandResponseJsonOutputTests(unittest.TestCase):
    def _json_output(self, response: CommandResponse) -> dict:
        formatted = ResponseFormatter(response, JSON_VIEW).prettify_response()
        return json.loads(formatted)

    def test_voiceover_json_meta_includes_domain_status(self):
        resp = CommandResponse(
            message='Voiceover is up to date',
            task_id='iam_theory',
            status='up_to_date',
            Status='SUCCESS',
        )
        out = self._json_output(resp)
        self.assertEqual(out['status'], SUCCESS_STATUS)
        self.assertEqual(out['code'], 200)
        self.assertEqual(out['message'], 'Voiceover is up to date')
        self.assertEqual(
            out['meta'],
            {'task_id': 'iam_theory', 'status': 'up_to_date'},
        )

    def test_error_json_uses_http_code_for_top_level_status(self):
        resp = CommandResponse(message='Error', Status='FAILED', code=400)
        out = self._json_output(resp)
        self.assertEqual(out['status'], ERROR_STATUS)
        self.assertEqual(out['code'], 400)


if __name__ == '__main__':
    unittest.main()
