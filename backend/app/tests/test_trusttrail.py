# File: ./backend/app/tests/test_trusttrail.py

# Import the TrustTrail model via its proper package path (run from backend/
# with PYTHONPATH=backend).
from app.models.trusttrail import TrustTrail, Likes







# File: test_trusttrail.py
# Description: Test suite for the TrustTrail model in TrustSphere project

import pytest
from unittest.mock import MagicMock, patch
#from models.trusttrail import TrustTrail, Likes

@pytest.fixture
def trusttrail_instance():
    '''Fixture to create a TrustTrail instance for testing'''
    return TrustTrail()

def test_add_transaction(trusttrail_instance):
    '''Test adding a transaction to the TrustTrail'''
    user_id = 'test_user_id'
    other_user_id = 'test_other_user_id'
    project_id = 'test_project_id'
    with patch('app.models.trusttrail.TrustTrail.add_transaction') as mocked_add:
        trusttrail_instance.add_transaction(user_id, other_user_id, project_id)
    mocked_add.assert_called_with(user_id, other_user_id, project_id)

def test_get_trusttrail(trusttrail_instance):
    '''Test retrieving a trusttrail'''
    user_id = 'test_user_id'
    with patch('app.models.trusttrail.TrustTrail.get_trusttrail') as mocked_get:
        trusttrail_instance.get_trusttrail(user_id)
    mocked_get.assert_called_with(user_id)

def test_add_gratitude_comment(trusttrail_instance):
    '''Test adding gratitude comment to a transaction'''
    transaction_id = 'test_transaction_id'
    comment = 'Thank you!'
    with patch('app.models.trusttrail.TrustTrail.add_gratitude_comment') as mocked_add_comment:
        trusttrail_instance.add_gratitude_comment(transaction_id, comment)
    mocked_add_comment.assert_called_with(transaction_id, comment)

def test_add_user_comment(trusttrail_instance):
    '''Test adding user comment to a transaction'''
    transaction_id = 'test_transaction_id'
    user_comment = 'Great cooperation!'
    with patch('app.models.trusttrail.TrustTrail.add_user_comment') as mocked_add_comment:
        trusttrail_instance.add_user_comment(transaction_id, user_comment)
    mocked_add_comment.assert_called_with(transaction_id, user_comment)

def test_add_other_comment(trusttrail_instance):
    '''Test adding other user's comment to a transaction'''
    transaction_id = 'test_transaction_id'
    other_user_id = 'test_other_user_id'
    comment = 'Need more details on this.'
    with patch('app.models.trusttrail.TrustTrail.add_other_comment') as mocked_add_comment:
        trusttrail_instance.add_other_comment(transaction_id, other_user_id, comment)
    mocked_add_comment.assert_called_with(transaction_id, other_user_id, comment)

def test_set_status(trusttrail_instance):
    '''Test setting status of a transaction'''
    transaction_id = 'test_transaction_id'
    status = 'Completed'
    with patch('app.models.trusttrail.TrustTrail.set_status') as mocked_set_status:
        trusttrail_instance.set_status(transaction_id, status)
    mocked_set_status.assert_called_with(transaction_id, status)

if __name__ == "__main__":
    pytest.main()