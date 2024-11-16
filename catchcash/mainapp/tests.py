from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Account, Wallet, Statement, Scope, FixStatement, Mission, Preset
from django.utils import timezone
from .forms import WalletFilterForm, StatementForm
from django.core.files.uploadedfile import SimpleUploadedFile

class ViewsTestCase(TestCase):

    def setUp(self):
        # Create test users
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.account = Account.objects.create(user=self.user, name="Test Account", appTheme="light")
        self.wallet = Wallet.objects.create(account=self.account, wName="Test Wallet", currency="USD", listCategory=["food", "transport"])
        
    def test_setting_view(self):
        response = self.client.get(reverse('setting'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'setting.html')

    def test_main_view_with_scope(self):
        
        self.statement1 = Statement.objects.create(wallet=self.wallet, amount=100, type='in', category="Salary", addDate=timezone.now())
        self.statement2 = Statement.objects.create(wallet=self.wallet, amount=50, type='out', category="Food", addDate=timezone.now())
        
        self.scope1 = Scope.objects.create(wallet=self.wallet, amount=1000, type='out', category='Saving', range='1M')
        
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        self.assertIn('form', response.context)
        self.assertIn('statements', response.context)
        self.assertIn('wallet', response.context)
        
    def test_main_no_wallet(self):
        self.wallet.delete()
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        self.assertIn('form', response.context)
        self.assertIn('statements', response.context)
        self.assertIn('wallet', response.context)
        
    def test_about_view(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'about.html')
        
    def test_main_form(self):
        self.client.login(username="testuser", password="testpassword")
        params = {
            "wallet":self.wallet.id,
            "date": "2024-11-15"
        }
        response = self.client.get(reverse('main'), data=params)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        self.assertIn('form', response.context)
        self.assertIn('statements', response.context)
        self.assertIn('wallet', response.context)

    def test_analysis_view(self):
        # Make a GET request to the 'analysis' view
        response = self.client.get(reverse('analysis'))  # Make sure 'analysis' is the correct URL name
        
        # Check that the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        
        # Check if the correct template is used
        self.assertTemplateUsed(response, 'analysis.html')
        
        # Check that the context contains 'data' and 'labels'
        self.assertIn('data', response.context)
        self.assertIn('labels', response.context)
        
        # Check that the 'data' context contains the expected list of numbers
        self.assertEqual(response.context['data'], [10, 20, 30, 40, 50])
        
        # Check that the 'labels' context contains the expected list of strings
        self.assertEqual(response.context['labels'], ["A", "B", "C", "D", "E"])
        
    def test_add_statement_view(self):
        statement_data1 = {
            'wallet_id': self.wallet.id,
            'category': 'food',
            'amount': 100.50,
            'type': 'in',
            'addDate': timezone.now().date()
        }
        
        statement_data2 = {
            'wallet_id': self.wallet.id,
            'category': 'other',
            'custom_category' : 'book',
            'amount': 50.50,
            'type': 'out',
            'addDate': timezone.now().date()
        }

        response = self.client.post(reverse('add_statement'), statement_data1)
        response = self.client.post(reverse('add_statement'), statement_data2)
        
        self.assertEqual(response.status_code, 302)  # Redirects after POST
        self.assertEqual(Statement.objects.count(), 2)
        statement = Statement.objects.first()
        self.assertEqual(statement.wallet, self.wallet)
        self.assertEqual(statement.amount, 100.50)
    
    def test_get_add_statement_view(self):
        response = self.client.get(f"{reverse('add_statement')}?wallet_id={self.wallet.id}")
        self.assertEqual(response.status_code, 200)

        
    def test_edit_statement_view(self):
        statement = Statement.objects.create(wallet=self.wallet, amount=200.00, type='out', category='food')
        statement_id = statement.id
            
        updated_data = {
            'category': 'transport',
            'amount': 300.00,
            'type': 'in',
            'addDate': timezone.now().date()
        }
            
        response = self.client.post(reverse('edit_statement', args=[statement_id]), updated_data)
        self.assertEqual(response.status_code, 302)  # Redirects after POST
            
        statement.refresh_from_db()  # Reload the statement from the database
        self.assertEqual(statement.category, 'transport')
        self.assertEqual(statement.amount, 300.00)
        
    def test_edit_statement_view_other(self):
        statement = Statement.objects.create(wallet=self.wallet, amount=300.00, type='in', category='transport')
        statement_id = statement.id
        
        updated_data = {
            'category': 'other',
            'custom_category': 'book',
            'amount': 300.00,
            'type': 'in',
            'addDate': timezone.now().date()
        }
        
        response = self.client.post(reverse('edit_statement', args=[statement_id]), updated_data)
        self.assertEqual(response.status_code, 302)  # Redirects after POST
        
        statement.refresh_from_db()  # Reload the statement from the database
        self.assertEqual(statement.category, 'book')
        self.assertEqual(statement.amount, 300.00)
        
    def test_edit_statement_get(self):
        # Create a statement linked to the wallet
        self.statement = Statement.objects.create(
            wallet=self.wallet,
            amount=100.00,
            type='in',
            category='Test Category',
            addDate=timezone.now().date()
        )

        # Access the edit_statement view
        response = self.client.get(reverse('edit_statement', args=[self.statement.id]))

        # Check if the response is successful
        self.assertEqual(response.status_code, 200)

    def test_delete_statement_view(self):
        # Test deleting a statement.
        # Ensure a statement is removed from the database after deletion.
        
        statement = Statement.objects.create(wallet=self.wallet, amount=200.00, type='out', category='food')
        statement_id = statement.id
        
        response = self.client.post(reverse('delete_statement', args=[statement_id]))
        self.assertEqual(response.status_code, 302)  # Redirects after POST
        self.assertEqual(Statement.objects.count(), 0)  # Statement should be deleted
        
    def test_create_wallet_view(self):
        # Test the create wallet view.
        # Ensure a wallet is created and stored in the database.
        self.client.login(username="testuser", password="testpassword")
        wallet_data = {
            'wName': 'New Wallet',
            'currency': 'EUR',
            'listCategory': ['savings', 'investment']
        }
        
        response = self.client.post(reverse('create_wallet'), data=wallet_data)
        self.assertEqual(response.status_code, 302)  # Redirects after POST
        self.assertEqual(Wallet.objects.count(), 2)  # The initial wallet and the new one
        wallet = Wallet.objects.last()
        self.assertEqual(wallet.wName, 'New Wallet')
        self.assertEqual(wallet.currency, 'EUR')
    
    def test_create_wallet_get(self):
        # Log in the user to access the create wallet view
        self.client.login(username="testuser", password="testpassword")
        
        # Send a GET request to the create_wallet view
        response = self.client.get(reverse('create_wallet'))
        
        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

    def test_create_fixstatement_valid_data(self):
        # Define valid data for a new FixStatement
        data = {
            'wallet': self.wallet.id,
            'amount': 100.00,
            'type': 'in',  # 'in' or 'out'
            'category': 'Salary',
            'frequency': '1M'  # 1 Month
        }

        # Send a POST request to create a new FixStatement
        response = self.client.post(reverse('create_fixstatement'), data)
        self.assertEqual(response.status_code, 302)
        # Check if a FixStatement was created in the database
        self.assertEqual(FixStatement.objects.count(), 1)

        # Check if the created FixStatement's fields match the submitted data
        fixstatement = FixStatement.objects.first()
        self.assertEqual(fixstatement.wallet, self.wallet)
        self.assertEqual(fixstatement.amount, 100.00)
        self.assertEqual(fixstatement.type, 'in')
        self.assertEqual(fixstatement.category, 'Salary')
        self.assertEqual(fixstatement.frequency, '1M')
        
    def test_create_fixstatement_get(self):
        # Send a GET request to the view
        response = self.client.get(reverse('create_fixstatement'))

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
    
    def test_create_scope_post(self):
        self.data = {
            'wallet': self.wallet.id,
            'amount': 5000,
            'type': 'Out',
            'category': 'Food',
            'range':'1M'
        }

        # Send a POST request with valid data to create a new scope
        response = self.client.post(reverse('create_scope'), self.data)

        # Check if the scope is created (redirect or success status)
        self.assertEqual(response.status_code, 302)  # Redirect after a successful post

        # Check if the scope is actually created in the database
        self.assertEqual(Scope.objects.count(), 1)
        scope = Scope.objects.first()
        self.assertEqual(scope.wallet, self.wallet)
        self.assertEqual(scope.amount, 5000)
        self.assertEqual(scope.type, 'Out')
        self.assertEqual(scope.category, 'Food')
        self.assertEqual(scope.range, '1M')
        
    def test_create_scope_get(self):
        # Send a GET request to the view
        response = self.client.get(reverse('create_scope'))

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        
    def test_create_misson_post(self):
        self.data = {
            'wallet' : self.wallet.id,
            'mName' : 'Tokyo Trip',
            'dueDate' : '2025-01-01',
            'amount' : 10000,
            'pic' :  SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        }
        
        # Send a POST request with valid data to create a new mission
        response = self.client.post(reverse('create_mission'), self.data)

        # Check if the mission is created (redirect or success status)
        self.assertEqual(response.status_code, 302)  # Redirect after a successful post

        # Check if the mission is actually created in the database
        self.assertEqual(Mission.objects.count(), 1)
        mission = Mission.objects.first()
        self.assertEqual(mission.wallet, self.wallet)
        self.assertEqual(mission.mName, 'Tokyo Trip')
        self.assertEqual(mission.dueDate.isoformat(), '2025-01-01')
        self.assertEqual(mission.amount, 10000)
        
    def test_create_mission_get(self):
        # Send a GET request to the view
        response = self.client.get(reverse('create_mission'))

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        
    def test_create_preset_post_valid_data(self):
        self.valid_data = {
            'wallet': self.wallet.id,
            'name': 'New Preset',
        }
        # Send a POST request with valid data
        response = self.client.post(reverse('create_preset'), self.valid_data)

        # Check that the response redirects to the wallet detail page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('wallet_detail', args=[self.wallet.id]))

        # Verify the preset is created in the database
        self.assertEqual(Preset.objects.count(), 1)
        preset = Preset.objects.first()
        self.assertEqual(preset.name, 'New Preset')
        self.assertEqual(preset.wallet, self.wallet)
        
    def test_create_preset_get(self):
        # Send a GET request to the view
        response = self.client.get(reverse('create_preset'))

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
    
    def test_progression_view(self):
        response = self.client.get(reverse('progression'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'progression.html')
        
    def test_trophy_view(self):
        response = self.client.get(reverse('trophy'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trophy.html')
    
    def test_wallet_detail_view_for_nonexistent_wallet(self):
        response = self.client.get(reverse('wallet_detail', args=[9999]))
        self.assertEqual(response.status_code, 200)  # Should return 404 as the wallet does not exist

class ScopeViewTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.account = Account.objects.create(user=self.user, name="Test Account", appTheme="light")

        # Create a wallet for the account
        self.wallet = Wallet.objects.create(account=self.account, wName="Test Wallet", currency="USD")

        # Add some statements to the wallet
        Statement.objects.create(wallet=self.wallet, amount=100.00, type="in", category="Salary")
        Statement.objects.create(wallet=self.wallet, amount=50.00, type="out", category="Groceries")
        Statement.objects.create(wallet=self.wallet, amount=20.00, type="out", category="Transportation")

        # Login the test user
        self.client.login(username='testuser', password='testpassword')

    def test_scope_view_calculations(self):
        # Test income and out calculation
        response = self.client.get(reverse('scope'))
        
        
        sData = {"in": 100.00, "out": 70.00}  # Expected values from setup
        self.assertEqual(response.context.get('sData'), sData)


    def test_scope_date_filtering(self):
        # Create statements with different dates
        specific_date = '2024-11-16'
        Statement.objects.create(wallet=self.wallet, amount=50.00, type="in", addDate=specific_date)
        Statement.objects.create(wallet=self.wallet, amount=30.00, type="out", addDate='2024-11-16')

        # Test filtering by specific date
        response = self.client.get(reverse('scope'), {"date": specific_date, "wallet":self.wallet.id})
        statements = response.context.get('statements')

        self.assertIsNotNone(statements, "Statements should not be None in the context.")
        self.assertEqual(statements.count(), 5)  # Only one statement matches the date
        self.assertEqual(statements.first().addDate.isoformat(), specific_date)

        # Test filtering by a non-existent date
        response_no_match = self.client.get(reverse('scope'), {"date": '2024-11-15', "wallet": self.wallet.id})
        statements_no_match = response_no_match.context.get('statements')

        self.assertEqual(statements_no_match.count(), 0)  # No statements should match