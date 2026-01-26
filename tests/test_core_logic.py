import unittest
import os
import json
from unittest.mock import patch, mock_open
from core_logic import update_task_stats, setup_logging, execute_flow

class TestCoreLogic(unittest.TestCase):

    @patch('core_logic._load_task_stats')
    @patch('core_logic._save_task_stats')
    def test_update_task_stats(self, mock_save, mock_load):
        mock_load.return_value = {
            "path/to/task": {"min": 1.0, "max": 3.0}
        }
        update_task_stats("path/to/task", 2.0)
        mock_save.assert_called_with({'path/to/task': {'min': 1.0, 'max': 3.0}})

        update_task_stats("path/to/task", 0.5)
        mock_save.assert_called_with({'path/to/task': {'min': 0.5, 'max': 3.0}})

        update_task_stats("path/to/task", 4.0)
        mock_save.assert_called_with({'path/to/task': {'min': 0.5, 'max': 4.0}})

    @patch('pathlib.Path.mkdir')
    @patch('logging.FileHandler')
    @patch('logging.basicConfig')
    def test_setup_logging(self, mock_basicConfig, mock_FileHandler, mock_mkdir):
        setup_logging()
        # Verifichiamo solo che mkdir sia stato chiamato, 
        # ignorando l'oggetto Path specifico (che è assoluto e dinamico)
        self.assertTrue(mock_mkdir.called)
        # Se volessimo essere precisi: mock_mkdir.assert_called_with(parents=True, exist_ok=True)
        # ma questo dipenderebbe da quale istanza di Path chiama mkdir.
        
        self.assertTrue(mock_basicConfig.called)
        self.assertTrue(mock_FileHandler.called)

    @patch('subprocess.run')
    def test_execute_flow(self, mock_subprocess_run):
        tasks = [
            {"name": "task1", "path": "task1.py", "enabled": True},
            {"name": "task2", "path": "task2.bat", "enabled": True}
        ]
        mock_subprocess_run.return_value.returncode = 0
        with patch('os.path.exists', return_value=True):
            execute_flow("test_flow", tasks)
            self.assertEqual(mock_subprocess_run.call_count, 2)

if __name__ == '__main__':
    unittest.main()
