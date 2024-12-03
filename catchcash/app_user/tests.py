from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from mainapp.models import Account
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages

class AuthViewTests(TestCase):

    def test_login_view_get(self):
        # Ensure the login form is displayed
        response = self.client.get(reverse('auth'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login_register.html')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_register_view_get(self):
        # Ensure the registration form is displayed
        response = self.client.get(reverse('auth'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login_register.html')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_login_view_post_valid(self):
        User.objects.create_user(username='testuser', password='testpassword')
        response = self.client.post(reverse('auth'), {
            'login' : 'login',
            'username' : 'testuser',
            'password' : 'testpassword'
        })
        self.assertEqual(response.status_code, 302)

    def test_register_view_post_valid(self):
        # Test valid registration
        response = self.client.post(reverse('auth'), {
            'register': 'register',
            'username': 'newuser',
            'password': 'newpassword',
            'confirm_password': 'newpassword',
            'email': 'newuser@example.com',
            'name': 'TestUser',
            'appTheme': 'light'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_view_post_invalid(self):
        # Test invalid registration (password mismatch)
        response = self.client.post(reverse('auth'), {
            'register': 'register',
            'username': 'newuser',
            'password': 'newpassword',
            'confirm_password': 'differentpassword',  # Mismatched password
            'email': 'newuser@example.com',
        })
        
        messages = list(get_messages(response.wsgi_request))
        # Check that the form errors are properly returned in the context
        self.assertEqual(messages[0].message, 'Registration failed. Please check the details.')
        
        # Ensure that the form is re-rendered (status code 200)
        self.assertEqual(response.status_code, 200)

