from datetime import timedelta
import datetime
from decimal import Decimal
import json
from django.forms import ValidationError
from datetime import date, datetime 
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Account, Wallet, Statement, Scope, Mission, Preset, ProgressionNode
from django.utils import timezone
from .forms import WalletFilterForm, StatementForm, ScopeForm, SettingForm
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages

class MissionTest(TestCase):
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
        current_date = timezone.now()
        specific_date = datetime(current_date.year, current_date.month,1)
        
        Statement.objects.create(wallet=self.wallet, amount=Decimal('100.00'), type='in', addDate=timezone.now())
        Statement.objects.create(wallet=self.wallet, amount=Decimal('50.00'), type='out', addDate=timezone.now())
        Statement.objects.create(wallet=self.wallet, amount=Decimal('200.00'), type='in', addDate=specific_date)
        Statement.objects.create(wallet=self.wallet, amount=Decimal('70.00'), type='out', addDate=specific_date)
    
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
        
    def test_edit_mission_get(self):
        self.mission = Mission.objects.create(
            wallet=self.wallet,
            mName="Test Mission",
            dueDate='2024-12-31',
            curAmount=Decimal('200.00'),
            amount=Decimal('500.00'),
        )
        """Test if the edit mission page loads with the correct form."""
        response = self.client.get(reverse('edit_mission', kwargs={'mission_id': self.mission.id}))

        # Check if the response is successful
        self.assertEqual(response.status_code, 200)

        # Check if the correct template is used
        self.assertTemplateUsed(response, 'edit_mission.html')

        # Verify that the form is pre-filled with the mission's data
        self.assertContains(response, self.mission.mName)
        self.assertContains(response, self.mission.amount)
        
    def test_edit_mission_post_valid_data(self):
        self.mission = Mission.objects.create(
            wallet=self.wallet,
            mName="Test Mission",
            dueDate='2024-12-31',
            curAmount=Decimal('200.00'),
            amount=Decimal('500.00'),
        )
        
        self.edit_url = reverse('edit_mission', kwargs={'mission_id': self.mission.id})
        
        """Test if the mission is updated with valid data."""
        updated_data = {
            'mName': "Updated Mission Name",
            'dueDate': "2024-11-30",
            'amount': "600.00",
        }

        response = self.client.post(self.edit_url, updated_data)

        # Refresh the mission object from the database
        self.mission.refresh_from_db()

        # Check if the mission was updated correctly
        self.assertEqual(self.mission.mName, updated_data['mName'])
        self.assertEqual(self.mission.dueDate.isoformat(), updated_data['dueDate'])
        self.assertEqual(self.mission.amount, Decimal(updated_data['amount']))

        # Check if the user is redirected to the 'goal' page
        expected_redirect_url = reverse('goal', kwargs={'wallet_id': self.wallet.id})
        self.assertRedirects(response, expected_redirect_url)
        
    def test_delete_mission(self):
        self.mission = Mission.objects.create(
            wallet=self.wallet,
            mName="Test Mission",
            dueDate='2024-12-31',
            amount=Decimal('500.00'),
            curAmount=Decimal('100.00')
        )

        # URL for deleting the mission
        self.delete_url = reverse('delete_mission', kwargs={'mission_id': self.mission.id})

        """Test that the mission is deleted successfully."""
        response = self.client.get(self.delete_url)

        # Check if the mission is deleted from the database
        with self.assertRaises(Mission.DoesNotExist):
            self.mission.refresh_from_db()

        # Ensure the user is redirected to the 'goal' page with the wallet ID
        expected_redirect_url = reverse('goal', kwargs={'wallet_id': self.wallet.id})
        self.assertRedirects(response, expected_redirect_url)
    
    def test_mission_filter(self):
        """Test that a new mission is created when the form is valid."""
        # Data for the form submission (valid data)
        post_data = {
            'mName': 'Test Mission',
            'dueDate': '2024-12-31',
            'amount': Decimal('500.00')
        }
        self.url = reverse('goal', kwargs={'wallet_id': self.wallet.id})

        # Make a POST request to the mission page
        response = self.client.post(self.url, data=post_data)

        # Check if the mission is created in the database
        mission = Mission.objects.filter(wallet=self.wallet, mName='Test Mission').first()
        
        self.assertIsNotNone(mission)
        self.assertEqual(mission.mName, 'Test Mission')

        self.assertEqual(mission.dueDate, date(2024, 12, 31))
        self.assertEqual(mission.amount, Decimal('500.00'))

        # Ensure the user is redirected to the correct page (goal page for this wallet)
        expected_redirect_url = reverse('goal', kwargs={'wallet_id': self.wallet.id})
        self.assertRedirects(response, expected_redirect_url)
    
        
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
            amount=Decimal('10000.00')
        )
        self.scope = Scope.objects.create(wallet=self.wallet, month=1, year=2024, income_goal=1000, expense_goal=500)
        
        # Add statements
        Statement.objects.create(wallet=self.wallet, amount=100.00, type="in", category="Salary", addDate=date(2024, 1, 10))
        Statement.objects.create(wallet=self.wallet, amount=50.00, type="out", category="Food", addDate=date(2024, 1, 15))
        Statement.objects.create(wallet=self.wallet, amount=20.00, type="out", category="Transport", addDate=date(2024, 1, 20))
    
    def test_welcome_view_redirects_authenticated_user(self):
        # Log in the user
        self.client.login(username='testuser', password='testpassword')

        # Send a GET request to the welcome view
        response = self.client.get(reverse('welcome'))

        # Assert that it redirects to the 'main' page
        self.assertRedirects(response, reverse('main'))
        
    def test_welcome_view_renders_for_unauthenticated_user(self):
        # Send a GET request to the welcome view without logging in
        response = self.client.get(reverse('welcome'))

        # Assert that the welcome.html template is rendered
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'welcome.html')
    
    def test_wallet_balance(self):
        # Calculate expected balance
        total_in = Decimal('100.00')  # Sum of 'in' type statements
        total_out = Decimal('50.00') + Decimal('20.00')  # Sum of 'out' type statements
        expected_balance = total_in - total_out
        
        # Check balance method
        self.assertEqual(Decimal(self.wallet.balance()), expected_balance)
        
    def test_change_theme(self):
        # Call the change_theme method
        new_theme = "dark"
        self.account.change_theme(new_theme)

        # Verify that the appTheme is updated
        self.account.refresh_from_db()
        self.assertEqual(self.account.appTheme, new_theme)
    
    def test_change_name(self):
        # Call the change_name method
        new_name = "Updated Name"
        self.account.change_name(new_name)

        # Verify that the name is updated
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, new_name)

    def test_change_pic(self):
        # Call the change_pic method
        new_pic = "profile_photos/default.jpg"
        self.account.change_pic(new_pic)

        # Verify that the profile_pic is updated
        self.account.refresh_from_db()
        self.assertEqual(self.account.profile_pic, new_pic)
    
    def test_about_view(self):
        """Test if the about view renders correctly."""
        # Get the response for the about view
        response = self.client.get(reverse('about'))

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check if the correct template is used
        self.assertTemplateUsed(response, 'about.html')
        
    def test_remove_category(self):
        self.wallet = Wallet.objects.create(
            account=self.account,
            wName="Test Wallet",
            currency="USD",
            listCategory=["Food", "Transport", "Shopping"]
        )
        # Remove an existing category
        
        self.wallet.remove_category("Food")
        self.wallet.refresh_from_db()
        self.assertNotIn("Food", self.wallet.listCategory)

        # Try to remove a non-existent category
        initial_count = len(self.wallet.listCategory)
        self.wallet.remove_category("NonExistentCategory")
        self.wallet.refresh_from_db()
        self.assertEqual(len(self.wallet.listCategory), initial_count)
        
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
        
    def test_account_str_method(self):
        # Verify that __str__ returns the account name
        self.assertEqual(str(self.account), "Test Account")
        
    def test_wallet_str(self):
        # Test the __str__ method
        self.assertEqual(str(self.wallet), "Wallet: Test Wallet")
        

    def test_change_password(self):
        self.account.change_password('newpassword')
        self.client.login(username='testuser', password='newpassword')
        
    def test_main_view_with_scope(self):
        # Log in the test user
        self.client.login(username="testuser", password="testpassword")
        
        # Parameters for filtering
        params = {
            "wallet": self.wallet.id,
            "date": "2024-01-15"
        }
        
        # Call the main view with date filter
        response = self.client.get(reverse('main'), data=params)
        
        # Check if the response status code is OK
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        
        # Check if the correct context data is passed
        self.assertIn('form', response.context)
        self.assertIn('statements', response.context)
        self.assertIn('wallet', response.context)
        self.assertIn('status', response.context)
        
        # Verify that the scope status is calculated
        status = response.context['status']
        self.assertIsNotNone(status)  # Ensure status is not None
        
        # Check if the scope calculations are correct based on the selected date
        # For date "2024-01-15", only the "Salary" and "Food" statements should be included
        statements = response.context['statements']
        self.assertEqual(len(statements), 1)  # Only one statements should be returned

        # Verify the status calculation (income and expense goals)
        self.assertIn("รายรับเดือนนี้ยังน้อยกว่า 1000.00 USD อยู่ 900.00 USD", status['income_message'])
        self.assertIn("รายจ่ายยังอยู่ในเป้า", status['expense_message'])
        
    def test_main_view_without_scope(self):
        # Log in the test user
        self.client.login(username="testuser", password="testpassword")
        
        # Create a wallet without a scope
        wallet_without_scope = Wallet.objects.create(account=self.account, wName="No Scope Wallet", currency="USD")
        Statement.objects.create(wallet=wallet_without_scope, amount=100.00, type="in", category="Salary", addDate=date(2024, 1, 10))
        
        # Call the main view without any scope
        params = {
            "wallet": wallet_without_scope.id,
            "date": "2024-01-10"
        }
        response = self.client.get(reverse('main'), data=params)
        
        # Check if the response status code is OK
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        
        # Check if the correct context data is passed
        self.assertIn('form', response.context)
        self.assertIn('statements', response.context)
        self.assertIn('wallet', response.context)
        self.assertIn('status', response.context)
        
        # # Verify that there is no status if no scope is present
        # status = response.context['status']
        # self.assertEqual(status['income_message'], "ไม่พบข้อมูลเป้าหมายสำหรับเดือนนี้")
        # self.assertEqual(status['expense_message'], "ไม่พบข้อมูลเป้าหมายสำหรับเดือนนี้")
    
    def test_main_view_with_empty_wallet(self):
        # Log in the test user
        self.client.login(username="testuser", password="testpassword")
        
        # Remove the wallet and check if a default wallet is created
        self.wallet.delete()
        
        # Call the main view
        response = self.client.get(reverse('main'))
        
        # Verify that the response redirects to the main view
        self.assertEqual(response.status_code, 302)  # Redirect to 'main'
        self.assertRedirects(response, reverse('main'))
        
        # Verify that a default wallet is created
        wallets = Wallet.objects.filter(account=self.account)
        self.assertEqual(wallets.count(), 1)  # Ensure one wallet is created
        default_wallet = wallets.first()
        self.assertEqual(default_wallet.wName, "Default Wallet")  # Default wallet name
        self.assertEqual(default_wallet.account, self.account)  # Linked to the correct account
        
    def test_main_view_creates_default_wallet(self):
        # Log in as the created user
        self.client.login(username="testuser", password="testpassword")
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
        
    def test_main_form_no_wallet(self):
        self.client.login(username="testuser", password="testpassword")
        self.wallet.delete()
        form = WalletFilterForm(account=self.account)
        
        # Check the empty label of the wallet field
        self.assertEqual(form.fields['wallet'].empty_label, "ไม่พบ Wallet")
    
    def test_wallet_not_found_case(self):
        # Remove the wallet to simulate the case where the wallet doesn't exist
        self.wallet.delete()
        
        # Log in the user
        self.client.login(username="testuser", password="testpassword")
        
        # Call the main view
        response = self.client.get(reverse('main'))
        
        # Check that the response redirects, meaning the default wallet is created
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('main'))
        
        # Check that a default wallet was created
        wallets = Wallet.objects.filter(account=self.account)
        self.assertEqual(wallets.count(), 1)
        default_wallet = wallets.first()
        self.assertEqual(default_wallet.wName, "Default Wallet")
        
    def test_date_not_provided_case(self):
        # Log in the user
        self.client.login(username="testuser", password="testpassword")
        
        # Test case where no date is provided
        params = {
            "wallet": self.wallet.id,  # Provide a valid wallet ID
        }
        
        # Call the main view without a date parameter
        response = self.client.get(reverse('main'), data=params)
        
        # Check if the date is correctly set to the current date in the response context
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        
        # Check if the dateText in context is set to the default "แสดงทั้งหมด (default)"
        self.assertEqual(response.context['date'], "แสดงทั้งหมด (default)")
        
        # Check if the `statements` are ordered and filtered correctly
        statements = response.context['statements']
        self.assertGreater(len(statements), 0)  # Ensure there are statements returned
        self.assertEqual(response.context['summary']['income'], 100.00)
        self.assertEqual(response.context['summary']['expense'], 70.00)
        self.assertEqual(response.context['summary']['net'], 30.00)
        
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
        self.assertEqual(Statement.objects.count(), 5)
        statement = Statement.objects.first()
        self.assertEqual(statement.wallet, self.wallet)
        self.assertEqual(statement.amount, 100.0)
    
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
        self.assertEqual(Statement.objects.count(), 3)
        
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
        
    def test_create_mission_post(self):
        self.data = {
            'wallet': self.wallet.id,
            'mName': 'Tokyo Trip',
            'dueDate': '2025-01-01',
            'amount': 10000,
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
        
    def test_create_goal_get(self):
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
        
    def test_delete_mission(self):
        self.mission.delete_mission()
        self.assertEqual(Mission.objects.count(), 0)
        
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

    
    def test_wallet_detail_view_for_nonexistent_wallet(self):
        response = self.client.get(reverse('wallet_detail', args=[9999]))
        self.assertEqual(response.status_code, 200)  # Should return 404 as the wallet does not exist

    def test_donate_successful(self):
        # Donate amount
        response = self.client.post(reverse('donate_to_mission', args=[self.mission.id]), {'donate_amount': '50.00'})
        
        # Check if donation was successful
        self.assertEqual(response.status_code, 302)  # Expecting a redirect
        
        # Check if statement is created
        self.assertEqual(Statement.objects.filter(wallet=self.wallet).count(), 4)
        statement = Statement.objects.last()
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
        self.assertEqual(Statement.objects.filter(wallet=self.wallet).count(), 3)
        
    def test_donate_exceeds_target(self):
        
        # Donate more than the amount needed
        response = self.client.post(reverse('donate_to_mission', args=[self.mission.id]), {'donate_amount': '100000.00'})
        # Expecting an error message and redirect
        self.assertRedirects(response, "/", status_code=302)
        
        message = list(get_messages(response.wsgi_request))
        self.assertEqual(message[0].message,"Amount exceeds the target left.")
        
        # No donation should be made
        self.assertEqual(Statement.objects.filter(wallet=self.wallet).count(), 3)
        
    def test_donate_invalid_amount(self):
        
        # Donate more than the amount needed
        response = self.client.post(reverse('donate_to_mission', args=[self.mission.id]), {'donate_amount': 'Invalid Amount'})
        
        # Expecting an error message and redirect
        self.assertRedirects(response, "/", status_code=302)
        
        message = list(get_messages(response.wsgi_request))
        self.assertEqual(message[0].message, "Invalid donation amount.")
        
        # No donation should be made
        self.assertEqual(Statement.objects.filter(wallet=self.wallet).count(), 3)
    
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
        self.assertEqual(statements.count(), 4)

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
        self.assertEqual(statements.count(), 4)

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
        
    
class ScopeTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.account = Account.objects.create(user=self.user, name="Test Account", appTheme="light")

        # Create a wallet for the account
        self.wallet = Wallet.objects.create(account=self.account, wName="Test Wallet", currency="USD")

        self.scope = Scope.objects.create(wallet=self.wallet, month=1, year=2024, income_goal=15000, expense_goal=5000)
        
        # Add some statements to the wallet
        Statement.objects.create(wallet=self.wallet, amount=100.00, type="in", category="Salary", addDate=date(2024, 1, 10))
        Statement.objects.create(wallet=self.wallet, amount=50.00, type="out", category="Groceries", addDate=date(2024, 1, 15))
        Statement.objects.create(wallet=self.wallet, amount=20.00, type="out", category="Transportation", addDate=date(2024, 1, 20))
        
        # Login the test user
        self.client.login(username='testuser', password='testpassword')
        
    def test_str_method(self):
        self.assertEqual(str(self.scope), 'Wallet: Test Wallet - 1/2024')
        
    def test_no_date_provided(self):
        # Test case where no date is provided, should use current date
        status = self.scope.calculate_status()

        # Assert that the status contains the correct income and expense messages
        self.assertEqual(status['income_diff'], None)  # income_goal - total_income (15000 - 100)
        self.assertEqual(status['expense_diff'], None)  # expense_goal - total_expense (5000 - 200)
        self.assertIn('ไม่พบข้อมูลเป้าหมายสำหรับเดือนนี้', status['income_message'])  # Message confirming the income goal is met
        self.assertIn('ไม่พบข้อมูลเป้าหมายสำหรับเดือนนี้', status['expense_message'])  # Message confirming the expense goal is met

    def test_date_not_matching_month_or_year(self):
        # Test case where date does not match the month/year of the scope
        status = self.scope.calculate_status(date=date(2023, 12, 1))

        # Assert that the status returns a message saying no data is available for this month
        self.assertEqual(status['income_diff'], None)
        self.assertEqual(status['expense_diff'], None)
        self.assertEqual(status['income_message'], "ไม่พบข้อมูลเป้าหมายสำหรับเดือนนี้")
        self.assertEqual(status['expense_message'], "ไม่พบข้อมูลเป้าหมายสำหรับเดือนนี้")

    def test_date_matching_month_and_year(self):
        # Test case where the date matches the month and year
        status = self.scope.calculate_status(date=date(2024, 1, 1))

        # Assert that the status calculates income and expense differences correctly
        self.assertEqual(status['income_diff'], -14900)  # income_goal - total_income (15000 - 100)
        self.assertEqual(status['expense_diff'], -4930)  # expense_goal - total_expense (5000 - 70)
        self.assertIn('รายรับเดือนนี้ยังน้อยกว่า 15000 USD อยู่ 14900.00 USD', status['income_message'])  # Message confirming income goal is met
        self.assertIn("รายจ่ายยังอยู่ในเป้า", status['expense_message'])  # Message confirming expense goal is met

    def test_no_statements(self):
        # Test case where no statements are created, so total_income and total_expense are both 0
        self.wallet.statements.all().delete()  # Clear all statements

        status = self.scope.calculate_status(date=date(2024, 1, 1))

        # Assert that no income or expense is recorded and appropriate messages are returned
        self.assertEqual(status['income_diff'], -15000)  # Should be less than the income_goal
        self.assertEqual(status['expense_diff'], -5000)  # Should be less than the expense_goal
        self.assertIn("รายรับเดือนนี้ยังน้อยกว่า", status['income_message'])  # Income less than goal
        self.assertIn("รายจ่ายยังอยู่ในเป้า", status['expense_message'])  # Expense within goal

    def test_income_less_than_goal(self):
        # Test case where total income is less than goal
        Statement.objects.create(wallet=self.wallet, amount=8000, type="in", category="Salary", addDate=date(2024, 1, 10))

        status = self.scope.calculate_status(date=date(2024, 1, 1))

        # Assert that the income is less than the goal and the message is correct
        self.assertEqual(status['income_diff'], -6900)  # income_goal - total_income (15000 - 8000 -100)
        self.assertIn("รายรับเดือนนี้ยังน้อยกว่า", status['income_message'])  # Income less than goal

    def test_expense_greater_than_goal(self):
        # Test case where total expense is greater than goal
        Statement.objects.create(wallet=self.wallet, amount=6000, type="out", category="Shopping", addDate=date(2024, 1, 10))

        status = self.scope.calculate_status(date=date(2024, 1, 1))

        # Assert that the expense is greater than the goal and the message is correct
        self.assertEqual(status['expense_diff'], 1070)  # total_expense - expense_goal (6000 + 70 - 5000)
        self.assertIn("รายจ่ายเดือนนี้เกินกว่า", status['expense_message'])  # Expense greater than goal

    def test_create_scope_successful_post(self):
        self.scope_url = reverse('create_scope')
        data = {
            'wallet': self.wallet.id,
            'month': 2,
            'year': 2024,
            'income_goal': 10000,
            'expense_goal': 4000,
        }
        response = self.client.post(self.scope_url, data)

        # Ensure a Scope is created
        self.assertEqual(Scope.objects.count(), 2)
        scope = Scope.objects.last()
        self.assertEqual(scope.wallet, self.wallet)
        self.assertEqual(scope.month, data['month'])
        self.assertEqual(scope.year, data['year'])
        self.assertEqual(scope.income_goal, data['income_goal'])
        self.assertEqual(scope.expense_goal, data['expense_goal'])

        # Check the redirect behavior
        self.assertRedirects(response, '/main')

    def test_create_scope_duplicate_scope(self):
        self.scope_url = reverse('create_scope')
        # Attempt to create another scope with the same wallet, month, and year
        data = {
            'wallet': self.wallet.id,
            'month': 1,
            'year': 2024,
            'income_goal': 20000,
            'expense_goal': 6000,
        }
        response = self.client.post(self.scope_url, data)

        # Assert that the second attempt does not create a new Scope
        self.assertEqual(Scope.objects.count(), 1)

        # Assert that the response status code indicates an error (if view returns error)
        self.assertEqual(response.status_code, 200)

        # Check the response for the error message
        self.assertContains(response, "ERROR, Can't create 2 scope with same month")

    def test_create_scope_get_request(self):
        self.scope_url = reverse('create_scope')
        response = self.client.get(self.scope_url)

        # Check the response status code
        self.assertEqual(response.status_code, 200)

        # Check the response for the error message
        self.assertContains(response, "ERROR, Can't create_scope")
        
    def test_edit_scope_get(self):
        self.edit_url = reverse('edit_scope', kwargs={'scope_id': self.scope.id})

        response = self.client.get(self.edit_url)

        # Check if the response is successful
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ERROR, Can't edit_scope")
        
    def test_edit_scope_post_valid_data(self):
        # URL for editing the scope
        self.edit_url = reverse('edit_scope', kwargs={'scope_id': self.scope.id})
        
        """Test that the scope is updated successfully with valid data."""
        updated_data = {
            'income_goal' : 30000,
            'expense_goal' : 20000
        }
        
        response = self.client.post(self.edit_url, updated_data)
        
        # Refresh the scope object from the database
        self.scope.refresh_from_db()
        # Check if the scope was updated correctly
        self.assertEqual(self.scope.income_goal, updated_data['income_goal'])
        self.assertEqual(self.scope.expense_goal, updated_data['expense_goal'])
        # Check if the user is redirected to the 'scope' page for the wallet
        self.assertRedirects(response, '/main')
        
    def test_delete_scope(self):
        # Confirm that the scope instance is created
        self.assertEqual(Scope.objects.count(), 1)

        # Perform the delete action
        response = self.client.get(reverse('delete_scope', kwargs={'scope_id': self.scope.id}))

        # Confirm the scope is deleted
        self.assertEqual(Scope.objects.count(), 0)

        # Check that the response redirects to the correct URL (redirect to 'scope' view with wallet_id)
        self.assertRedirects(response, '/main')
        
class AnalysisTest(TestCase):
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
        
class ProgressionTest(TestCase):
    
    def setUp(self):
        """Set up test data."""
        # Create a test user and account
        self.user = User.objects.create_user(username='testuser', password='password')
        self.account = Account.objects.create(user=self.user, name="Test Account", appTheme="light")
        
        # Create wallets for the user
        self.wallet1 = Wallet.objects.create(account=self.account, wName="Wallet 1", currency="USD", listCategory=["Food", "Transport"])
        self.wallet2 = Wallet.objects.create(account=self.account, wName="Wallet 2", currency="USD", listCategory=["Food", "Shopping"])
        
        # Create statements for the wallets
        Statement.objects.create(wallet=self.wallet1, amount=Decimal('100.00'), type='in', addDate=timezone.now() - timedelta(days=1))
        Statement.objects.create(wallet=self.wallet1, amount=Decimal('50.00'), type='out', addDate=timezone.now() - timedelta(days=2))
        Statement.objects.create(wallet=self.wallet2, amount=Decimal('200.00'), type='in', addDate=timezone.now() - timedelta(days=3))
        Statement.objects.create(wallet=self.wallet2, amount=Decimal('100.00'), type='out', addDate=timezone.now() - timedelta(days=4))

        # Create some scopes (just to check if they are counted)
        Scope.objects.create(wallet=self.wallet1, month=1, year=2024, income_goal=15000, expense_goal=5000)
        Scope.objects.create(wallet=self.wallet2, month=1, year=2024, income_goal=10000, expense_goal=4000)
        

        # Create missions for the wallets
        self.mission1 = Mission.objects.create(wallet=self.wallet1, mName="Mission 1", amount=Decimal('500.00'), dueDate=timezone.now() + timedelta(days=10))
        self.mission2 = Mission.objects.create(wallet=self.wallet2, mName="Mission 2", amount=Decimal('200.00'), dueDate=timezone.now() + timedelta(days=20))
        
        # Set up a successful mission for testing (curAmount >= amount)
        self.mission1.curAmount = Decimal('500.00')
        self.mission1.save()
        
        # Set URL for the progression view
        self.url = reverse('progression')
        self.client.login(username='testuser', password='password')

    def test_progression_view_successful_mission(self):
        """Test progression view when there is at least one successful mission."""
        response = self.client.get(self.url)
        
        # Assert that the response contains the correct context
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['has_successful_mission'])  # We expect a successful mission

    def test_progression_view_no_successful_mission(self):
        """Test progression view when no mission is successful."""
        # Make the mission unsuccessful (curAmount < amount)
        self.mission1.curAmount = Decimal('0.00')
        self.mission1.save()

        # Also make mission2 unsuccessful
        self.mission2.curAmount = Decimal('0.00')
        self.mission2.save()

        response = self.client.get(self.url)
        
        # Assert that the response contains the correct context
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['has_successful_mission'])  # No successful mission now

    def test_progression_view_context_data(self):
        """Test if the context values are correct."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wallet_count'], 2)  # Two wallets
        self.assertEqual(response.context['preset_count'], 0)  # No presets created in this test
        self.assertEqual(response.context['mission_count'], 2)  # Two missions
        self.assertEqual(response.context['scope_count'], 2)  # Two scopes
        self.assertEqual(response.context['total_income'], Decimal('300.00'))  # Total income from wallets
        
class ProgressionNodeModelTest(TestCase):

    def setUp(self):
        """Set up test data."""
        # Create a ProgressionNode instance
        self.node = ProgressionNode.objects.create(name="Node 1", description="This is a test node.")

    def test_str_method(self):
        """Test the __str__ method of the ProgressionNode model."""
        self.assertEqual(str(self.node), "Node 1")  # Check if the string representation is the same as the name
        
class GoalViewTestCase(TestCase):

    def setUp(self):
        # Create test user and account
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.account = Account.objects.create(user=self.user, name="Test Account", appTheme="light")
        
        # Create a wallet for the account
        self.wallet = Wallet.objects.create(account=self.account, wName="Test Wallet", currency="USD")
        
        # Create missions associated with the wallet
        self.mission1 = Mission.objects.create(
            wallet=self.wallet,
            mName="Save for vacation",
            dueDate=timezone.now().date(),
            curAmount=Decimal("200.00"),
            amount=Decimal("1000.00"),
        )
        self.mission2 = Mission.objects.create(
            wallet=self.wallet,
            mName="Emergency fund",
            dueDate=timezone.now().date(),
            curAmount=Decimal("500.00"),
            amount=Decimal("500.00"),
        )

    def test_no_wallet_creates_default(self):
        # Remove the wallet to simulate no existing wallets
        self.wallet.delete()

        # Log in the user
        self.client.login(username="testuser", password="testpassword")

        # Call the goal view
        response = self.client.get(reverse('goal'))

        # Check that the response redirects to the main page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('main'))

        # Check that a default wallet was created
        wallets = Wallet.objects.filter(account=self.account)
        self.assertEqual(wallets.count(), 1)
        default_wallet = wallets.first()
        self.assertEqual(default_wallet.wName, "Default Wallet")

    def test_goals_displayed_correctly(self):
        # Log in the user
        self.client.login(username="testuser", password="testpassword")

        # Call the goal view
        response = self.client.get(reverse('goal'))

        # Check that the response is 200 and uses the correct template
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'goal.html')

        # Check that the missions are included in the context
        goals = response.context['goals']
        self.assertEqual(goals.count(), 2)
        self.assertIn(self.mission1, goals)
        self.assertIn(self.mission2, goals)

    def test_mission_amount_to_go(self):
        # Verify the `amountToGo` calculation
        self.assertEqual(self.mission1.amountToGo(), Decimal("800.00"))
        self.assertEqual(self.mission2.amountToGo(), Decimal("0.00"))

    def test_mission_donation_success(self):
        # Make a donation to the mission
        self.mission1.donate(Decimal("300.00"))

        # Refresh the mission from the database
        self.mission1.refresh_from_db()

        # Verify the updated current amount
        self.assertEqual(self.mission1.curAmount, Decimal("500.00"))

        # Verify a statement was created
        statement = Statement.objects.filter(wallet=self.wallet, amount=Decimal("300.00")).first()
        self.assertIsNotNone(statement)
        self.assertEqual(statement.type, "out")
        self.assertEqual(statement.category, "แบ่งจ่ายรายการใหญ่")

    def test_mission_donation_exceeds_target(self):
        with self.assertRaises(ValidationError):
            self.mission1.donate(Decimal("900.00"))  # Exceeds the remaining target

    def test_mission_donation_invalid_amount(self):
        with self.assertRaises(ValidationError):
            self.mission1.donate(Decimal("-100.00"))  # Negative amount

    def test_mission_successful_status(self):
        # Test mission success status
        self.assertTrue(self.mission2.is_successful())
        self.assertFalse(self.mission1.is_successful())

    def test_mission_outdate_status(self):
        # Test outdated status
        self.assertFalse(self.mission1.isOutdate())

        # Update the due date to a past date
        self.mission1.dueDate = timezone.now().date().replace(year=2023)
        self.mission1.save()

        self.assertTrue(self.mission1.isOutdate())

    def test_mission_status_text(self):
        # Test the status text
        self.assertEqual(
            self.mission1.status_text(),
            "[Save for vacation] 800.00USD more!"
        )
        self.assertEqual(
            self.mission2.status_text(),
            "[Emergency fund] 500.00/500.00USD (100.00%)"
        )

    def test_date_in_context(self):
        # Log in the user
        self.client.login(username="testuser", password="testpassword")

        # Call the goal view
        response = self.client.get(reverse('goal'))

        # Check that the date is included in the context and matches today's date
        self.assertIn('date', response.context)
        self.assertEqual(response.context['date'], timezone.now().date())
        
    def test_form_valid_wallet_selected(self):
        # Log in the user
        self.client.login(username="testuser", password="testpassword")
        
        # Simulate a valid form submission with a specific wallet selected
        response = self.client.get(reverse('goal'), {'wallet': self.wallet.id})
        
        # Check the selected wallet in context
        self.assertEqual(response.context['wallet'], self.wallet)

    def test_form_valid_no_wallet_provided(self):
        # Log in the user
        self.client.login(username="testuser", password="testpassword")
        
        # Simulate a valid form submission with no wallet provided
        response = self.client.get(reverse('goal'), {})
        
        # Check the default wallet in context
        self.assertEqual(response.context['wallet'], self.wallet)

    def test_form_invalid_falls_back_to_default_wallet(self):
        # Log in the user
        self.client.login(username="testuser", password="testpassword")
        
        # Simulate an invalid form submission
        response = self.client.get(reverse('goal'), {'invalid_field': 'invalid_value'})
        
        # Check the default wallet in context
        self.assertEqual(response.context['wallet'], self.wallet)
        
class SettingViewTest(TestCase):
    def setUp(self):
        # Create a test user and associated account
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.account = Account.objects.create(user=self.user, name='Test User', appTheme='light')

        # Log in the test user
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('setting')

    def test_setting_view_get(self):
        """Test if the setting page renders correctly on GET request."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'setting.html')
        self.assertIn('setting_form', response.context)
        self.assertIn('account', response.context)

    def test_setting_view_post_valid_data(self):
        """Test if valid POST data updates the account and redirects."""
        valid_data = {
            'name': 'Updated Name',
            'appTheme': 'dark',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
            'profile_pic': '',  # Assuming no new file upload
        }
        response = self.client.post(self.url, valid_data)

        # Check if the account was updated
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, 'Updated Name')
        self.assertEqual(self.account.appTheme, 'dark')

        # Ensure the password was updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))

        # Check the redirect
        self.assertEqual(response.status_code, 302)  # Ensure it's a redirect
        self.assertEqual(response.url, reverse('main'))  # Check the redirection URL

    def test_setting_view_post_invalid_password(self):
        """Test if mismatched passwords result in an error."""
        invalid_data = {
            'name': 'Another Name',
            'appTheme': 'light',
            'password': 'newpassword123',
            'confirm_password': 'differentpassword',
            'profile_pic': '',
        }
        response = self.client.post(self.url, invalid_data)

        # Ensure the response status code is 200 (form re-rendered with errors)
        self.assertEqual(response.status_code, 200)

        # Retrieve the form from the response context
        form = response.context['setting_form']

        # Check if the form contains the expected error
        self.assertIn('Passwords do not match.', form.errors['confirm_password'])

    def test_setting_view_post_no_password_change(self):
        """Test if other fields update without changing the password."""
        partial_data = {
            'name': 'Partial Update',
            'appTheme': 'dark',
            'password': '',
            'confirm_password': '',
            'profile_pic': '',
        }
        response = self.client.post(self.url, partial_data)

        # Reload the account from the database
        self.account.refresh_from_db()

        # Check if the fields were updated
        self.assertEqual(self.account.name, 'Partial Update')
        self.assertEqual(self.account.appTheme, 'dark')

        # Ensure the password remains unchanged
        self.assertTrue(self.user.check_password('testpassword'))

        # Check the redirect
        self.assertEqual(response.status_code, 302)  # Ensure it's a redirect
        self.assertEqual(response.url, reverse('main'))  # Check the redirection URL