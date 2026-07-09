# A Smarty us_street candidate payload, shaped like Smarty-samples/valid-address.json.
mock_smarty_candidate = {
  "input_index": 0,
  "candidate_index": 0,
  "delivery_line_1": "4567 Other St",
  "last_line": "San Francisco CA 94102-1234",
  "components": {
    "primary_number": "4567",
    "street_name": "Other",
    "street_suffix": "St",
    "city_name": "San Francisco",
    "state_abbreviation": "CA",
    "zipcode": "94102",
    "plus4_code": "1234"
  },
  "analysis": {
    "dpv_match_code": "Y",
    "enhanced_match": "postal-match"
  }
}

mock_smarty_validated_address = {
  "streetAddress": "4567 Other St",
  "secondaryAddress": "",
  "city": "San Francisco",
  "state": "CA",
  "ZIPCode": "94102",
  "ZIPPlus4": "1234",
  "urbanization": ""
}

# Same address, but with a secondary unit. Mirrors the "809 S Lamar Blvd Apt 214" sample,
# where delivery_line_1 folds the unit into the street line but components keep them apart.
mock_smarty_candidate_with_secondary = {
  "input_index": 0,
  "candidate_index": 0,
  "delivery_line_1": "809 S Lamar Blvd Apt 214",
  "components": {
    "primary_number": "809",
    "street_predirection": "S",
    "street_name": "Lamar",
    "street_suffix": "Blvd",
    "secondary_number": "214",
    "secondary_designator": "Apt",
    "city_name": "Austin",
    "state_abbreviation": "TX",
    "zipcode": "78704",
    "plus4_code": "1565"
  },
  "analysis": {
    "dpv_match_code": "Y",
    "enhanced_match": "postal-match"
  }
}

# Mirrors Smarty-samples/invalid-address-tx_de.json: Smarty matched the address only by
# discarding part of the input, so dpv_match_code is still "Y".
mock_smarty_candidate_ignored_input = {
  "input_index": 0,
  "candidate_index": 0,
  "delivery_line_1": "809 S Lamar Blvd Apt 214",
  "components": {
    "primary_number": "809",
    "street_predirection": "S",
    "street_name": "Lamar",
    "street_suffix": "Blvd",
    "secondary_number": "214",
    "secondary_designator": "Apt",
    "city_name": "Austin",
    "state_abbreviation": "TX",
    "zipcode": "78704",
    "plus4_code": "1565"
  },
  "analysis": {
    "dpv_match_code": "Y",
    "footnotes": "B#",
    "enhanced_match": "postal-match,ignored-input"
  }
}