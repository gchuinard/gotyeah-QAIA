Feature: Health endpoint
  As an operator
  I want a health endpoint
  So that I can monitor the service

  Scenario: health returns ok
    Given the service is running
    When I GET /health
    Then the response status is 200
    And the response body field "status" equals "ok"
