import requests
from flask import json, jsonify, request

from . import app

# Internal function to get a token for accessing the API
def gettoken():

    #Every application/integration gets a unique ClientId/ClientSecret-combination.
    #The application is created in Visma Developer Portal.
    client_id = 'vsas_payroll_demo_app' 
    client_secret = 'NjjMtTILZBhbvMfTiwChMtZSSnDWCFoOQgUgJCZsaOfcXCeLQKeTFtSZytqoBcDN'

    #Every company in Visma.net Payroll has a unique Tenant_id.
    #A connection needs to be established between your client and the tenant to enable access.
    tenant_id = 'a4586720-500d-11eb-9852-0638767d04b5'

    #The authentication uses standard OAuth2.0 with the Client Credentials flow
    reqdata = 'grant_type=client_credentials'
    reqdata += '&scope=payroll:employees:read payroll:paycodes:read payroll:transactions:full'
    reqdata += '&client_id=' + client_id
    reqdata += '&client_secret=' + client_secret
    reqdata += '&tenant_id=' + tenant_id

    # Sends token request to Visma Connect to receive authentication-token
    response = requests.post('https://connect.visma.com/connect/token',
                             data=reqdata,
                             headers={
                                 'Content-Type': 'application/x-www-form-urlencoded'
                             }
                             )

    # Successful authentication results in HTTP 200 response.
    # The response includes the following JSON-package
    # {
    #   "access_token": "eyJhbGc....",
    #   "expires_in": 3600,
    #   "token_type": "Bearer",
    #   "scope": "visma_api:read"
    # }
    if response.status_code == 200:
        json_data = json.loads(response.text)

        return json_data["access_token"]

# Internal function to get the positions of a specific employee.
def getpositions(empid):
    response = requests.get('https://api.payroll.core.hrm.visma.net/v1/query/employees/' + empid,
                            headers={
                                'Authorization': 'Bearer ' + gettoken(),
                                'accept': 'application/json'
                            }
                            )

    if response.status_code == 200:
        json_data = json.loads(response.text)

        return json_data["positions"]

# Internal function to query data from the API. This method takes in the endpoint to query, the request-params and a cursor-token to support paging
def querydata(endpoint, requestparams, cursor):

    # Adds the cursor-token to the request-params
    if cursor != None:
        if requestparams == None:
            requestparams = {'cursor': cursor}
        else:
            requestparams['cursor'] = cursor

    # Make the request to the API
    response = requests.get('https://api.payroll.core.hrm.visma.net/v1/query/' + endpoint,
                            headers={
                                'Authorization': 'Bearer ' + gettoken(),
                                'accept': 'application/json'
                            },
                            params=requestparams
                            )

    # All successful requests returns HTTP Status 200
    if response.status_code == 200:
        # Parses the response JSON
        json_data = json.loads(response.text)

        # If there is a cursor-element present in the response, this means that there are more pages of information available.
        if 'cursor' in json_data:
            # We extract the cursor-token to use for further calls
            nextToken = json_data['cursor']['nextToken']
        else:
            nextToken = None

        # Returns the requested data (from the element 'data' in the JSON), also returns the cursor-token if available.
        return json_data['data'], nextToken

# Function to return a list of employees to the GUI. Enpoint accessible at route GET /payroll/getemployees
@app.route("/payroll/getemployees", methods=["GET"])
def getemployees():

    # Uses the internal function "querydata" to perform the query. The function returns the data, and the optional cursor-token to get 
    # the next page of results. No requestparams are given, since we want to get all the employees 
    data, cursor = querydata('employees', None, None)

    # Adds the data to a local variable in case there are more pages of results we need to merge
    employees = data

    # If the query returns a cursor-token, this means that there are more pages of results. We create a loop to keep getting the results
    # until there are no more pages (cursor-token is None).
    while cursor != None:
        data, cursor = querydata('employees', None, cursor)
        employees.extend(data)
        pass

    # Returns the employee-list to the UI as JSON
    return jsonify(employees)

# Function to return a list of paycodes to the GUI. Enpoint accessible at route GET /payroll/getpaycodes
@app.route("/payroll/getpaycodes", methods=["GET"])
def getpaycodes():

    # We only want the paycodes of type Time, therefore we add a request-param for paycodeType
    params = {
        'paycodeType': 'Time'
    }

    # Uses the internal function "querydata" to perform the query. The function returns the data, and the optional cursor-token to get 
    # the next page of results. We include our list of request-params, since we want to get all the paycodes 
    data, token = querydata('paycodes', params, None)

    # Adds the data to a local variable in case there are more pages of results we need to merge
    paycodes = data

    # If the query returns a cursor-token, this means that there are more pages of results. We create a loop to keep getting the results
    # until there are no more pages (cursor-token is None).
    while token != None:
        data, token = querydata('paycodes', None, token) # Here we don't include the request-parameters because the cursortoken will continue the list based on previous params. 
        paycodes.extend(data)
        pass

    # Returns the employee-list to the UI as JSON
    return jsonify(paycodes)

# Function to create a new transaction. Used by the UI to create transactions based on the users choice
@app.route("/payroll/createtransaction", methods=["POST"])
def createtransaction():
    # Extracts the request data (JSON) from the request
    data = request.json

    # Gets a list of the positions for the given employee (required for creating a transaction)
    positions = getpositions(data["employeeid"])

    # Creates the JSON data for the request
    transactiondata = {
        'paycodeId': data["paycodeid"],
        'employeeId': data["employeeid"],
        'positionId': positions[0]["id"],
        'quantity': int(data["quantity"]),
        'price': int(data["price"]),
        'activeStart': '2021-01-17',
        'activeEnd': '2021-01-17'
    }

    # Makes POST the request to the Payroll API, to create the transaction
    response = requests.post('https://api.payroll.core.hrm.visma.net/v1/command/transaction/create',
                             headers={
                                 'Authorization': 'Bearer ' + gettoken(),
                                 'Content-type': 'application/json'
                             },
                             json=transactiondata
                             )

    # Successful creation of the transaction returns HTTP 202 (Accepted)
    if response.status_code == 202:
        # When creating a transaction the job is done asynchrounously by Visma.net Payroll. 
        # Therefore the output of the call is a link to the job created, to check the status and result of the job we need 
        # to call the jobstatus-endpoint
        # The url to call the jobstatus-endpoint, including the jobid, is delivered in the http-header "Location" of the reponse.
        location = response.headers['Location']

        # The Location-value returns the url to the endpoint ex: /v1/command/transaction/jobs/12344894389384. To extract the job-id we split up the string.
        jobid = location.split('/')
        jobid = jobid[len(jobid) - 1]

        # Returns the jobid to the UI
        return jobid

# Function to get and return the status of a job
@app.route("/payroll/getjobstatus/<jobid>", methods=["GET"])
def getjobstatus(jobid):

    # Makes the request to the jobstatus-endpoint with the jobid as parameter
    response = requests.get('https://api.payroll.core.hrm.visma.net/v1/command/transaction/jobs/' + jobid,
                            headers={
                                'Authorization': 'Bearer ' + gettoken(),
                                'accept': 'application/json'
                            }
                            )

    # Successful requests return HTTP 200
    if response.status_code == 200:
        json_data = json.loads(response.text)

        # The status of the task is returned to the UI
        return json_data['status']
