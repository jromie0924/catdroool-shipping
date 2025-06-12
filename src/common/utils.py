import re

ZIP_REGEX = r'^\d{5}(-\d{4})?$'

def get_time_difference_hours(start: int, end: int):
  return float(end - start) / 1000.0 / 60.0 / 60.0


def populate_shipment_record(customer: dict, usps_verified_address: dict) -> dict:
  shipping_info = customer['shipping']['address'] if customer['shipping'] and customer['shipping']['address'] else {}
  line_2_visibility: bool = bool(usps_verified_address.get("secondaryAddress") or shipping_info.get('line2'))
  usps_city = f"{usps_verified_address.get('city')}"
  usps_state = f"{usps_verified_address.get('state')}"
  usps_zip = f"{usps_verified_address.get('ZIPCode')}-{usps_verified_address.get('ZIPPlus4')}"
  
  # Ensure that the constructed zip code is not "xxxx-"
  # If it is, then set the usps zip to "" and cause the default
  # back to the Stripe zip.
  match = re.match(ZIP_REGEX, usps_zip)
  if not match:
    usps_zip = ""
  
  line_3 = f"{usps_city or shipping_info.get('city')} {usps_state or shipping_info.get('state')} {usps_zip or shipping_info.get('city')}"
  record = {
    "CardName": customer.get('name'),
    "ShippingName": customer.get('shipping').get('name'),
    "ShippingAddressLine1": usps_verified_address.get("streetAddress") or shipping_info.get('line1'),
    "ShippingAddressLine2": usps_verified_address.get("secondaryAddress") or shipping_info.get('line2') or "",
    "#Line2Visibility": f"{line_2_visibility}",
    "ShippingAddressCity": usps_verified_address.get("city") or shipping_info.get('city'),
    "ShippingAddressState": usps_verified_address.get("state") or shipping_info.get('state'),
    "ShippingAddressPostalCode": usps_zip or shipping_info.get('postal_code'),
    "ShippingAddressLine3": line_3
  }
  
  return record