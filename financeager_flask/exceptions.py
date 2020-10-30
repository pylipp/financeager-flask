"""Expections of the financeager-flask plugin."""
from financeager.exceptions import FinanceagerException


class OfflineRecoveryError(FinanceagerException):
    """Error during recovering of offline backup."""
