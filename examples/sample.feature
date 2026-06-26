Feature: Users API
  As an API consumer
  I want to manage users
  So that the system has accounts

  Scenario: create a user
    Given the API is available
    When I POST /users with name "Ada" and email "ada@example.com"
    Then the response status is 201
    And the response body field "id" is present
    And the response body field "name" equals "Ada"

  Scenario: reject a user with a missing email
    Given the API is available
    When I POST /users with name "Ada" and no email
    Then the response status is 422

  Scenario: fetch an existing user
    Given a user with id 1 exists
    When I GET /users/1
    Then the response status is 200
    And the response body field "id" equals 1

  Scenario: fetch a missing user
    Given no user with id 999 exists
    When I GET /users/999
    Then the response status is 404
