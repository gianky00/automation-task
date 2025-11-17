import unittest
import os
import json
from unittest.mock import patch, MagicMock
from scheduler_service import scheduler_service, flow_execution_wrapper
import time

class TestSchedulerService(unittest.TestCase):

    @patch('scheduler_service.execute_flow')
    @patch('scheduler_service._update_status_file')
    def test_flow_execution_wrapper(self, mock_update, mock_execute):
        flow_execution_wrapper("test_flow", [])
        self.assertTrue(mock_update.called)
        self.assertTrue(mock_execute.called)

    @patch('scheduler_service.time.sleep', side_effect=InterruptedError)
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='{}')
    def test_scheduler_service_interrupt(self, mock_open, mock_sleep):
        with self.assertRaises(InterruptedError):
            scheduler_service()

if __name__ == '__main__':
    unittest.main()
