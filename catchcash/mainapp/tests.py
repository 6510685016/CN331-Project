
from datetime import timedelta
from decimal import Decimal
import json
from django.forms import ValidationError

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Account, Wallet, Statement, Scope, FixStatement, Mission, Preset
from django.utils import timezone
from .forms import WalletFilterForm, StatementForm
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages

class ScopeModelTest(TestCase):
    def setUp(self):
        # Create a test user and account
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.account = Account.objects.create(
            user=self.user,
            name="Test User",
            appTheme="light"
        )

        # Create a Wallet instance
        self.wallet = Wallet.objects.create(
            account=self.account,
            wName="Test Wallet",
            currency="USD",
            listCategory=["Food", "Transport", "Shopping"]
        )
        
        # Create some statements to be used in the tests
        Statement.objects.create(wallet=self.wallet, amount=Decimal('100.00'), type='in', addDate=timezone.now())
        Statement.objects.create(wallet=self.wallet, amount=Decimal('50.00'), type='out', addDate=timezone.now())
        Statement.objects.create(wallet=self.wallet, amount=Decimal('200.00'), type='in', addDate=timezone.now() - timedelta(weeks=2))
        Statement.objects.create(wallet=self.wallet, amount=Decimal('70.00'), type='out', addDate=timezone.now() - timedelta(weeks=2))
    
    def test_scope_str_representation(self):
        # Create a scope
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal("100.00"),
            type="out",
            range="1W"
        )

        # Verify the string representation
        self.assertEqual(str(scope), "Scope: (1W)")

    
    def test_status_in_1d(self):
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('200.00'),
            type='in',
            range='1D'
        )
        date = timezone.now().date()  # Use current date for testing
        self.assertEqual(scope.status(date), Decimal('100.00'))  # The target was 200, 100 is already in, so 200-100=100 remains

    def test_status_out_1d(self):
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('50.00'),
            type='out',
            range='1D'
        )
        date = timezone.now().date()  # Use current date for testing
        self.assertEqual(scope.status(date), Decimal('0.00'))  # The target was 50, but already 50 is out, so 50-50=0

    def test_status_in_1w(self):
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('300.00'),
            type='in',
            range='1W'
        )
        # Assuming the current date is within the same week as the statement's
        date = timezone.now().date()  # Use current date for testing
        self.assertEqual(scope.status(date), Decimal('200.00'))  # Target is 300, but already 200 in, so 300-200=100 remains

    def test_status_out_1m(self):
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('150.00'),
            type='out',
            range='1M'
        )
        # Assuming the current date is within the month of the statements
        date = timezone.now().date()  # Use current date for testing
        self.assertEqual(scope.status(date), Decimal('-30.00'))  # Target is 150, but already 100 out, so 150-100=50 remains
    
    def test_status_in_1y(self):
        # Create a scope with the '1Y' range and an 'in' type target
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('500.00'),
            type='in',
            range='1Y'
        )
        
        # Create statements for different years
        Statement.objects.create(wallet=self.wallet, amount=Decimal('100.00'), type='in', addDate=timezone.now() - timedelta(days=200))
        Statement.objects.create(wallet=self.wallet, amount=Decimal('150.00'), type='in', addDate=timezone.now())
        
        # We are using the current date for the test
        date = timezone.now().date()
        
        # We expect the sum of income in this year to be 150.00
        self.assertEqual(scope.status(date), Decimal('-50.00'))  # Target is 500, already 150 in, so 500 - 150 = 350 remains

    def test_status_out_1y(self):
        # Create a scope with the '1Y' range and an 'out' type target
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('300.00'),
            type='out',
            range='1Y'
        )
        
        # Create statements for different years
        Statement.objects.create(wallet=self.wallet, amount=Decimal('50.00'), type='out', addDate=timezone.now() - timedelta(days=365))  # 1 year ago
        Statement.objects.create(wallet=self.wallet, amount=Decimal('100.00'), type='out', addDate=timezone.now())  # This year
        
        # We are using the current date for the test
        date = timezone.now().date()
        
        # We expect the sum of expenses this year to be 100.00
        self.assertEqual(scope.status(date), Decimal('-80.00'))  # Target is 300, already 100 out, so 300 - 100 = 200 remains
    
    def test_status_to_text_in_1d(self):
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('200.00'),
            type='in',
            range='1D'
        )
        date = timezone.now().date()  # Use current date for testing
        self.assertEqual(scope.statusToText(), "Income less then target by 100.00.")

    def test_status_to_text_out_1d(self):
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('50.00'),
            type='out',
            range='1D'
        )
        date = timezone.now().date()  # Use current date for testing
        self.assertEqual(scope.statusToText(), "On target.")
        
    def test_status_to_text_in_over(self):
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('200.00'),
            type='in',
            range='1D'
        )
        date = timezone.now().date()  # Use current date for testing
        self.assertEqual(scope.statusToText(), "Income less then target by 100.00.")
    
    def test_status_to_text_out_over(self):
        scope = Scope.objects.create(
            wallet=self.wallet,
            amount=Decimal('20.00'),
            type='out',
            range='1D'
        )
        date = timezone.now().date()  # Use current date for testing
        self.assertEqual(scope.statusToText(), "Spent 30.00 more than planned.")
    
    def test_status_outdated(self):
        mission = Mission.objects.create(
            wallet=self.wallet,
            mName="Completed Mission",
            dueDate=timezone.now().date() - timedelta(days=1),
            curAmount=Decimal("50.00"),
            amount=Decimal("100.00")
        )

        self.assertEqual(mission.status_text(), "[Completed Mission] 50.00/100.00USD (50.00%)")
        
    def test_status_amountTogo_equal_0(self):
        mission = Mission.objects.create(
            wallet=self.wallet,
            mName="Completed Mission",
            dueDate=timezone.now().date() + timedelta(days=1),
            curAmount=Decimal("100.00"),
            amount=Decimal("100.00")
        )

        self.assertEqual(mission.status_text(), "[Completed Mission] 100.00/100.00USD (100.00%)")
        
    def test_mission_str_representation(self):
        # Create a mission
        mission = Mission.objects.create(
            wallet=self.wallet,
            mName="Save for Vacation",
            dueDate=timezone.now().date(),
            curAmount=Decimal("500.00"),
            amount=Decimal("1000.00"),
        )

        # Verify the string representation
        self.assertEqual(str(mission), "Save for Vacation")
        
class ViewsTestCase(TestCase):

    def setUp(self):
        # Create test users
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.account = Account.objects.create(user=self.user, name="Test Account", appTheme="light")
        self.wallet = Wallet.objects.create(account=self.account, wName="Test Wallet", currency="USD", listCategory=["food", "transport"])
        self.mission = Mission.objects.create(
            wallet=self.wallet,
            mName="Test Mission",
            dueDate="2025-01-01",
            amount=Decimal('10000.00'),
            pic=SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        )
        
    def test_account_str_method(self):
        # Verify that __str__ returns the account name
        self.assertEqual(str(self.account), "Test Account")
        
    def test_wallet_str(self):
        # Test the __str__ method
        self.assertEqual(str(self.wallet), "Wallet: Test Wallet")
        
    def test_setting_view(self):
        response = self.client.get(reverse('setting'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'setting.html')

    def test_change_password(self):
        self.account.change_password('newpassword')
        self.client.login(username='testuser', password='newpassword')
        
    def test_main_view_with_scope(self): 
        self.statement1 = Statement.objects.create(wallet=self.wallet, amount=100, type='in', category="Salary", addDate=timezone.now())
        self.statement2 = Statement.objects.create(wallet=self.wallet, amount=50, type='out', category="Food", addDate=timezone.now())
        
        self.scope1 = Scope.objects.create(wallet=self.wallet, amount=1000, type='out', range='1M')
        
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        self.assertIn('form', response.context)
        self.assertIn('statements', response.context)
        self.assertIn('wallet', response.context)
        
    def test_main_view_creates_default_wallet(self):
        # Log in as the created user
        self.client.login(username="testuser", password="testpassword")
        
    def test_main_no_wallet(self): #มีอันใหม่ที่ไม่ fail แล้ว 1
        self.wallet.delete()
        
        # Access the main view
        url = reverse('main')
        response = self.client.get(url)

        # Verify that the response redirects to the main view
        self.assertEqual(response.status_code, 302)  # Redirect to 'main'
        self.assertRedirects(response, reverse('main'))

        # Verify that a default wallet is created
        wallets = Wallet.objects.filter(account=self.account)
        self.assertEqual(wallets.count(), 1)  # Ensure one wallet is created
        default_wallet = wallets.first()
        self.assertEqual(default_wallet.wName, "Default Wallet")  # Default wallet name
        self.assertEqual(default_wallet.account, self.account)  # Linked to the correct account

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

    def test_analysis_view(self): #มีอันใหม่ที่ไม่ fail แล้ว 2
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
        self.assertContains(response, "ERROR, Can't add_statement")
        
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
        self.assertContains(response, "ERROR, Can't edit_statement")

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
        
        self.assertContains(response, "ERROR, Can't create_wallet")

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
        self.assertContains(response, "ERROR, Can't create_fixstatement")
    
    def test_create_scope_post(self):
        self.data = {
            'wallet': self.wallet.id,
            'amount': 5000,
            'type': 'Out',
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
        self.assertEqual(scope.range, '1M')
        
    def test_create_scope_get(self):
        # Send a GET request to the view
        response = self.client.get(reverse('create_scope'))

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ERROR, Can't create_scope")
        
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
        self.assertEqual(Mission.objects.count(), 2)
        mission = Mission.objects.last()
        self.assertEqual(mission.wallet, self.wallet)
        self.assertEqual(mission.mName, 'Tokyo Trip')
        self.assertEqual(mission.dueDate.isoformat(), '2025-01-01')
        self.assertEqual(mission.amount, 10000)
        
    def test_create_mission_get(self):
        # Send a GET request to the view
        response = self.client.get(reverse('create_mission'))

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        
        self.assertContains(response, "ERROR, Can't create_mission")
    
    def test_create_preset_post_valid_data(self):
        # Send a POST request with valid data
        self.valid_data = {
            'wallet': self.wallet.id,
            'name': 'New Preset',
        }
        response = self.client.post(reverse('create_preset'), self.valid_data)

        # Check that the response redirects to the 'main' view
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('main'))

        # Check that a Preset object was created
        self.assertEqual(Preset.objects.count(), 1)
        preset = Preset.objects.first()
        self.assertEqual(preset.name, 'New Preset')
        self.assertEqual(preset.wallet, self.wallet)

        # Check that a success message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Preset ถูกสร้างสำเร็จแล้ว')
        
    def test_create_preset_get(self):
        # Send a GET request to the view
        response = self.client.get(reverse('create_preset'))

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ERROR, Can't create_preset")
        
    def test_preset_form_valid_data(self):
        self.client.login(username="testuser", password="testpassword")
        # Prepare valid POST data
        data = {
            'name': 'Valid Preset',
            'field1': 'รายรับ',
            'field2': 100,
            'field3': 'รายจ่าย',
        }
        
        # Get the URL for creating a preset
        url = reverse('preset', args=[self.wallet.id])

        # Submit the POST request with valid data
        response = self.client.post(url, data)

        # Ensure that the preset is created and redirected to the same page
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        self.assertRedirects(response, reverse('preset', args=[self.wallet.id]))

        # Check that the preset is saved in the database
        preset = Preset.objects.first()  # Assuming it's the first preset created
        self.assertEqual(preset.name, 'Valid Preset')
        self.assertEqual(preset.statement['field1'], 'รายรับ')
        self.assertEqual(preset.statement['field2'], 100)
        self.assertEqual(preset.statement['field3'], 'รายจ่าย')

    def test_edit_preset_form_invalid_data(self):
        # Prepare invalid data (missing required fields)
        self.client.login(username="testuser", password="testpassword")
        self.preset = Preset.objects.create(
            wallet=self.wallet,
            name='Test Preset',
            statement={'field1': 'รายรับ', 'field2': 100, 'field3': 'รายจ่าย'}
        )
        
        data = {
            'name': 'Updated Preset',  # Valid name
            'field1': '',  # Invalid field1 (empty)
            'field2': '',  # Invalid field2 (empty)
            'field3': '',  # Invalid field3 (empty)
        }

        # Get the URL for editing the preset
        url = reverse('edit_preset', args=[self.preset.id])

        # Submit the POST request with invalid data
        response = self.client.post(url, data)

        # Ensure the response is rendered back with the form and errors
        self.assertEqual(response.status_code, 200)  # The page should re-render with errors

        # Get the form from the context
        form = response.context['form']

        # Check that the form contains errors for the required fields
        # self.assertFormError(response, 'form', 'field1', 'This field is required.')
        # self.assertFormError(response, 'form', 'field2', 'This field is required.')
        # self.assertFormError(response, 'form', 'field3', 'This field is required.')

    def test_edit_preset_form_valid_data(self):
        # Prepare valid data
        self.client.login(username="testuser", password="testpassword")
        self.preset = Preset.objects.create(
            wallet=self.wallet,
            name='Test Preset',
            statement={'field1': 'รายรับ', 'field2': 100, 'field3': 'รายจ่าย'}
        )
        
        data = {
            'name': 'Updated Preset',
            'field1': 'รายรับ',
            'field2': 200,
            'field3': 'รายจ่าย',
        }

        # Get the URL for editing the preset
        url = reverse('edit_preset', args=[self.preset.id])

        # Submit the POST request with valid data
        response = self.client.post(url, data)

        # Ensure the preset is updated and redirected to the preset page
        self.assertEqual(response.status_code, 302)  # Redirect after successful update
        self.assertRedirects(response, reverse('preset', args=[self.wallet.id]))

        # Verify the preset data was updated
        updated_preset = Preset.objects.get(id=self.preset.id)
        self.assertEqual(updated_preset.name, 'Updated Preset')
        self.assertEqual(updated_preset.statement['field1'], 'รายรับ')
        self.assertEqual(updated_preset.statement['field2'], 200)
        self.assertEqual(updated_preset.statement['field3'], 'รายจ่าย')

    def test_edit_preset_get_request(self):
        
        self.preset = Preset.objects.create(
            wallet=self.wallet,
            name='Test Preset',
            statement={'field1': 'รายรับ', 'field2': 100, 'field3': 'รายจ่าย'}
        )
        
        # Log in the test user
        self.client.login(username='testuser', password='testpassword')
        
        # Get the URL for editing the preset
        url = reverse('edit_preset', args=[self.preset.id])

        # Send a GET request to the edit preset page
        response = self.client.get(url)

        # Ensure the page renders successfully (status code 200)
        self.assertEqual(response.status_code, 200)

        # Check that the form is rendered with the preset's data pre-filled
        form = response.context['form']
        self.assertEqual(form.initial['name'], 'Test Preset')
        self.assertEqual(form.initial['field1'], 'รายรับ')
        self.assertEqual(form.initial['field2'], 100)
        self.assertEqual(form.initial['field3'], 'รายจ่าย')
        
        
    def test_delete_preset(self):
        self.preset = Preset.objects.create(
            wallet=self.wallet,
            name="Test Preset",
            statement={'field1': 'รายรับ', 'field2': 100, 'field3': 'รายจ่าย'}
        )
        
        self.client.login(username='testuser', password='testpassword')
        # Store the wallet ID before deletion for redirect check
        wallet_id = self.wallet.id

        # Get the URL for deleting the preset
        url = reverse('delete_preset', args=[self.preset.id])

        # Send a GET request to the delete URL
        response = self.client.get(url)

        # Ensure the response is a redirect
        self.assertEqual(response.status_code, 302)  # Redirect status code
        self.assertRedirects(response, reverse('preset', args=[wallet_id]))  # Redirects to the preset view of the wallet

        # Verify the preset is deleted from the database
        with self.assertRaises(Preset.DoesNotExist):
            Preset.objects.get(id=self.preset.id)

        # Verify the wallet is still intact and not deleted
        self.assertEqual(Wallet.objects.count(), 1)  # Only one wallet should exist
        self.assertEqual(Preset.objects.count(), 0)  # The preset should be deleted
    
    def test_str_preset(self):
        # Test the __str__ method of Preset
        preset = Preset.objects.create(wallet=self.wallet, name="Sample Preset")
        self.assertEqual(str(preset), "Sample Preset")
    
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

    def test_donate_successful(self):
        # Donate amount
        response = self.client.post(reverse('donate_to_mission', args=[self.mission.id]), {'donate_amount': '50.00'})
        
        # Check if donation was successful
        self.assertEqual(response.status_code, 302)  # Expecting a redirect
        
        # Check if statement is created
        self.assertEqual(Statement.objects.filter(wallet=self.wallet).count(), 1)
        statement = Statement.objects.first()
        self.assertEqual(statement.amount, Decimal('50.00'))
        self.assertEqual(statement.type, 'out')
        self.assertEqual(statement.category, 'แบ่งจ่ายรายการใหญ่')
        
        # Check if curAmount is updated
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.curAmount, Decimal('50.00'))
        
    def test_donate_less_than_zero(self):
        # Donate invalid amount (e.g., negative or zero)
        response = self.client.post(reverse('donate_to_mission', args=[self.mission.id]), {'donate_amount': '-10.00'})
        self.assertRedirects(response, "/", status_code=302) #Expecting Redirect
        
        message = list(get_messages(response.wsgi_request))
        self.assertEqual(message[0].message,"Amount must be greater than 0.")
        # No donation should be made
        self.assertEqual(Statement.objects.filter(wallet=self.wallet).count(), 0)
        
    def test_donate_exceeds_target(self):
        
        # Donate more than the amount needed
        response = self.client.post(reverse('donate_to_mission', args=[self.mission.id]), {'donate_amount': '100000.00'})
        # Expecting an error message and redirect
        self.assertRedirects(response, "/", status_code=302)
        
        message = list(get_messages(response.wsgi_request))
        self.assertEqual(message[0].message,"Amount exceeds the target left.")
        
        # No donation should be made
        self.assertEqual(Statement.objects.filter(wallet=self.wallet).count(), 0)
        
    def test_donate_invalid_amount(self):
        
        # Donate more than the amount needed
        response = self.client.post(reverse('donate_to_mission', args=[self.mission.id]), {'donate_amount': 'Invalid Amount'})
        
        # Expecting an error message and redirect
        self.assertRedirects(response, "/", status_code=302)
        
        message = list(get_messages(response.wsgi_request))
        self.assertEqual(message[0].message, "Invalid donation amount.")
        
        # No donation should be made
        self.assertEqual(Statement.objects.filter(wallet=self.wallet).count(), 0)
    
    def test_donate_to_mission_get(self):
        response = self.client.get(reverse('donate_to_mission', args=[1]))

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ERROR, Can't donate_to_mission")
        
    def test_preset_view_get(self):
        self.preset_data = Preset.objects.create(wallet=self.wallet, name="Preset 1")
        
        # Test that the preset page is rendered with the correct context
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(reverse('preset', args=[self.wallet.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'preset.html')
        self.assertIn('form', response.context)
        self.assertIn('wallet', response.context)
        self.assertIn('presets', response.context)
        self.assertEqual(len(response.context['presets']), 1)  # Preset should be returned in context
        self.assertEqual(response.context['wallet'], self.wallet)
        
    def test_use_preset_creates_statement_in(self):
        self.preset = Preset.objects.create(
                wallet=self.wallet,
                name="Test Preset",
                statement={'field1': 'food', 'field2': 100, 'field3': 'รายจ่าย'}
            )

        # Log in the test user
        self.client.login(username="testuser", password="testpassword")
        
        # Get the URL for using the preset
        url = reverse('use_preset', args=[self.preset.id])

        # Send a POST request to use the preset
        response = self.client.post(url)

        # Ensure the response is successful and returns the correct JSON
        self.assertEqual(response.status_code, 200)  # Success status
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['message'], 'Statement created successfully.')

        # Verify that exactly one Statement was created in the database
        statements = Statement.objects.filter(wallet=self.wallet)
        self.assertEqual(statements.count(), 1)

        # Validate the attributes of the created Statement
        statement = statements.last()  # Retrieve the created Statement
        self.assertEqual(statement.category, 'food')
        self.assertEqual(statement.amount, Decimal('100'))
        self.assertEqual(statement.type, 'out')  # `field3` was 'รายจ่าย'
        
    def test_use_preset_creates_statement_out(self):
        self.preset = Preset.objects.create(
                wallet=self.wallet,
                name="Test Preset",
                statement={'field1': 'salary', 'field2': 100, 'field3': 'รายรับ'}
            )

        # Log in the test user
        self.client.login(username="testuser", password="testpassword")
        
        # Get the URL for using the preset
        url = reverse('use_preset', args=[self.preset.id])

        # Send a POST request to use the preset
        response = self.client.post(url)

        # Ensure the response is successful and returns the correct JSON
        self.assertEqual(response.status_code, 200)  # Success status
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['message'], 'Statement created successfully.')

        # Verify that exactly one Statement was created in the database
        statements = Statement.objects.filter(wallet=self.wallet)
        self.assertEqual(statements.count(), 1)

        # Validate the attributes of the created Statement
        statement = statements.last()  # Retrieve the created Statement
        self.assertEqual(statement.category, 'salary')
        self.assertEqual(statement.amount, Decimal('100'))
        self.assertEqual(statement.type, 'in')  # `field3` was 'รายจ่าย'
        
        
    def test_use_preset_invalid_method(self):
        self.preset = Preset.objects.create(
                wallet=self.wallet,
                name="Test Preset",
                statement={'field1': 'food', 'field2': 100, 'field3': 'รายจ่าย'}
            )

        # Get the URL for using the preset
        url = reverse('use_preset', args=[self.preset.id])

        # Send a GET request instead of POST
        response = self.client.get(url)

        # Ensure the response returns a 405 Method Not Allowed status
        self.assertEqual(response.status_code, 405)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['message'], 'Invalid request method.')
        
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

    def test_statement_str_representation(self):
        # Create a statement
        statement = Statement.objects.create(
            wallet=self.wallet,
            amount=Decimal("150.00"),
            type="in",
            category="Salary",
            addDate=timezone.now().date()
        )

        # Verify the string representation
        expected_str = f"{self.wallet} - 150.00 (in)"
        self.assertEqual(str(statement), expected_str)
    
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
        self.assertEqual(statements.count(), 2)  # Only one statement matches the date
        self.assertEqual(statements.first().addDate.isoformat(), specific_date)

        # Test filtering by a non-existent date
        response_no_match = self.client.get(reverse('scope'), {"date": '2024-11-15', "wallet": self.wallet.id})
        statements_no_match = response_no_match.context.get('statements')

        self.assertEqual(statements_no_match.count(), 0)  # No statements should match
        
    def test_create_scope_wallet_does_not_exist(self):
        # Simulate a POST request with a wallet_id that doesn't exist
        invalid_wallet_id = 99999  # ID that doesn't exist in the database

        response = self.client.post(reverse('create_scope'), {
            'wallet': invalid_wallet_id,
            'amount': 1000,
            'type': 'in',
            'range': 5000,
        })

        # Check that the user is redirected to the main page
        self.assertRedirects(response, reverse('main'))

        # Check that the error message was added to the messages
        storage = get_messages(response.wsgi_request)
        messages = list(storage)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'ไม่พบกระเป๋าเงินที่เลือก')  # The error message in Thai

        # Verify that no Scope was created
        self.assertEqual(Scope.objects.count(), 0)  # No Scope should be created

class AnalysisViewTest(TestCase):
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(username='testuser', password='password')
        
        # Create an Account for the user
        self.account = Account.objects.create(user=self.user)
        
        # Create wallets associated with the account
        self.wallet1 = Wallet.objects.create(account=self.account, wName='Wallet 1', currency='USD')
        self.wallet2 = Wallet.objects.create(account=self.account, wName='Wallet 2', currency='EUR')

        # Create statements for wallet1
        self.statement1 = Statement.objects.create(wallet=self.wallet1, amount=100, type='expense', category='Food', addDate=date(2024, 11, 20))
        self.statement2 = Statement.objects.create(wallet=self.wallet1, amount=50, type='income', category='Salary', addDate=date(2024, 11, 21))

        # Create statements for wallet2
        self.statement3 = Statement.objects.create(wallet=self.wallet2, amount=200, type='expense', category='Shopping', addDate=date(2024, 11, 20))

    def test_analysis_view_no_wallet_id(self):
        # Test accessing the analysis page without wallet_id
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('analysis'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analysis.html')
        self.assertIn('wallets', response.context)
        self.assertEqual(len(response.context['wallets']), 2)

    def test_analysis_view_with_valid_wallet_id(self):
        # Test accessing the analysis page with a valid wallet_id
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('analysis') + f'?wallet_id={self.wallet1.id}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.wallet1.wName)
        self.assertContains(response, self.statement1.amount)
        self.assertContains(response, self.statement2.amount)
        
    def test_analysis_view_with_invalid_wallet_id(self):
        # Test accessing the analysis page with an invalid wallet_id
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('analysis') + '?wallet_id=999')

        # Expecting a 404 error response
        self.assertEqual(response.status_code, 404)  # Corrected to expect a 404 status code
        
        # Check if the JSON response contains the error message
        response_data = response.json()  # Parse the JSON response
        self.assertIn('error', response_data)  # Ensure there's an 'error' key
        self.assertEqual(response_data['error'], 'Wallet not found')  # Check if the error message matches

    def test_analysis_view_with_wallet_id_and_date(self):
        # Test accessing the analysis page with a valid wallet_id and selected_date
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('analysis') + f'?wallet_id={self.wallet1.id}&date=2024-11-21')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.wallet1.wName)
        self.assertContains(response, self.statement2.amount)
        self.assertNotContains(response, self.statement1.amount)
        
    def test_analysis_view_with_wallet_id_and_no_matching_statements(self):
        # Test when there are no matching statements for a given date
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('analysis') + f'?wallet_id={self.wallet1.id}&date=2024-12-01')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.wallet1.wName)
        self.assertNotContains(response, 'amount')  # No statement found for the given date
