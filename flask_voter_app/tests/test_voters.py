# import unittest
# from flask import Flask
# from flask.testing import FlaskClient
# from app import create_app # Import your app factory function
# import json

# class VotersTestCase(unittest.TestCase):
#     def setUp(self):
#         self.app = create_app()
#         self.client = self.app.test_client()

#     def test_get_voters(self):
#         response = self.client.get('/voters')
#         self.assertEqual(response.status_code, 200)
#         data = json.loads(response.data)
#         self.assertIsInstance(data, list)
#         self.assertGreater(len(data), 0)
#         for voter in data:
#             self.assertIn('id', voter)
#             self.assertIn('name', voter)

#     def test_get_voters_invalid_method(self):
#         response = self.client.post('/voters')
#         self.assertEqual(response.status_code, 405)
#           # Assuming POST is not allowed

# if __name__ == '__main__':
#     unittest.main()
