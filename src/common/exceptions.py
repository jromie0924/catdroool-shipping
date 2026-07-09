class RateLimitError(Exception):
  """
  Raised when the address validation API is still rate limiting us after the
  Smarty SDK has exhausted its own Retry-After backoff. Keeps callers from
  having to import the SDK's exception types.
  """

  def __init__(self, message: str = None):
    super().__init__(message or "Rate limited by the address validation API.")


class CredentialsError(Exception):
  """
  Raised when the address validation API credentials cannot be read out of AWS Secrets
  Manager, or are not in the expected "<auth-id>:<auth-token>" form. Aws.get_secret logs
  and returns None rather than raising, so a missing secret has to be caught here.
  """

  def __init__(self, message: str = None):
    super().__init__(message or "Could not load the address validation API credentials.")


class AddressNotFoundError(Exception):
  """
  Raised when Smarty returns no candidate for an address, meaning it could not be
  matched at all. The customer is left out of the shipping report entirely.
  """

  def __init__(self, message: str = None):
    super().__init__(message or "Address could not be matched by the address validation API.")
