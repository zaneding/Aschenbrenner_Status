import unittest

from tracker.portfolio import (
    classify_changes,
    parse_information_table,
    summarize_portfolio,
)


LATEST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>COREWEAVE INC</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>21873S108</cusip>
    <value>250000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>1000000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority><Sole>1000000</Sole><Shared>0</Shared><None>0</None></votingAuthority>
  </infoTable>
  <infoTable>
    <nameOfIssuer>BLOOM ENERGY CORP</nameOfIssuer>
    <titleOfClass>CL A</titleOfClass>
    <cusip>093712107</cusip>
    <value>125000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>500000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority><Sole>500000</Sole><Shared>0</Shared><None>0</None></votingAuthority>
  </infoTable>
  <infoTable>
    <nameOfIssuer>BLOOM ENERGY CORP</nameOfIssuer>
    <titleOfClass>CL A</titleOfClass>
    <cusip>093712107</cusip>
    <value>50000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>100000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <putCall>Call</putCall>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority><Sole>0</Sole><Shared>0</Shared><None>0</None></votingAuthority>
  </infoTable>
</informationTable>
"""


PREVIOUS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>COREWEAVE INC</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>21873S108</cusip>
    <value>200000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>800000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
  </infoTable>
  <infoTable>
    <nameOfIssuer>INTEL CORP</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>458140100</cusip>
    <value>100000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>250000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
  </infoTable>
</informationTable>
"""


class PortfolioTests(unittest.TestCase):
    def test_parse_information_table_extracts_holdings(self):
        holdings = parse_information_table(LATEST_XML)

        self.assertEqual(len(holdings), 3)
        self.assertEqual(holdings[0]["issuer"], "COREWEAVE INC")
        self.assertEqual(holdings[0]["cusip"], "21873S108")
        self.assertEqual(holdings[0]["value_usd"], 250_000)
        self.assertEqual(holdings[0]["shares"], 1_000_000)
        self.assertEqual(holdings[0]["share_type"], "SH")

    def test_summarize_portfolio_calculates_weights_and_totals(self):
        holdings = summarize_portfolio(parse_information_table(LATEST_XML))

        self.assertEqual(holdings["total_value_usd"], 425_000)
        self.assertEqual(holdings["position_count"], 3)
        self.assertEqual(holdings["holdings"][0]["weight"], 250_000 / 425_000)
        self.assertEqual(holdings["top_holding"]["issuer"], "COREWEAVE INC")

    def test_classify_changes_labels_position_activity(self):
        latest = parse_information_table(LATEST_XML)
        previous = parse_information_table(PREVIOUS_XML)

        changes = classify_changes(latest, previous)
        by_cusip = {change["cusip"]: change for change in changes}

        self.assertEqual(by_cusip["21873S108"]["status"], "increased")
        self.assertEqual(by_cusip["093712107"]["status"], "new")
        self.assertEqual(by_cusip["458140100"]["status"], "sold_out")
        self.assertEqual(by_cusip["21873S108"]["share_delta"], 200_000)

    def test_classify_changes_keeps_equity_and_options_separate(self):
        latest = parse_information_table(LATEST_XML)
        previous = parse_information_table(PREVIOUS_XML)

        changes = classify_changes(latest, previous)
        bloom_changes = [change for change in changes if change["cusip"] == "093712107"]

        self.assertEqual(len(bloom_changes), 2)
        self.assertEqual({change["position_type"] for change in bloom_changes}, {"Equity", "Call"})


if __name__ == "__main__":
    unittest.main()
