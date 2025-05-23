class ErrorCollection:
  
  FIELD_NAMES = ["Customer ID", "Issue", "Nationality"]
  
  def __init__(self):
    self.errors: list[dict] = []
  
  def add_new(self, customer_id: str, issue: str, nationality: str):
    self.errors.append({
      "Customer ID": customer_id,
      "Issue": issue,
      "Nationality": nationality
    })
