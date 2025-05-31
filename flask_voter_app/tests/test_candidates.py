import unittest
from flask import Flask
from flask.testing import FlaskClient
from app import create_app
import json

# class CandidatesTestCase(unittest.TestCase):
#     def setUp(self):
#         self.app = create_app()
#         self.client = self.app.test_client()

#     def test_get_candidates(self):
#         response = self.client.get('/candidates')
#         self.assertEqual(response.status_code, 200)
#         data = json.loads(response.data)
#         self.assertIsInstance(data, list)
#         self.assertGreater(len(data), 0)
#         for candidate in data:
#             self.assertIn('id', candidate)
#             self.assertIn('first_name', candidate)
#             self.assertIn('last_name', candidate)
    
#     def test_get_candidates_invalid_method(self):
#         response = self.client.post('/candidates')
#         self.assertEqual(response.status_code, 405)

# if __name__ == '__main__':
#     unittest.main()