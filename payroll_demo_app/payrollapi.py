from flask import json, jsonify, request
import requests

from . import app

def gettoken():

    client_id = 'vsas_payroll_demo_app'
    client_secret = 'NjjMtTILZBhbvMfTiwChMtZSSnDWCFoOQgUgJCZsaOfcXCeLQKeTFtSZytqoBcDN'
    tenant_id = 'a4586720-500d-11eb-9852-0638767d04b5'

    reqdata = 'grant_type=client_credentials'
    reqdata += '&scope=payroll:employees:read payroll:paycodes:read payroll:transactions:full'
    reqdata += '&client_id=' + client_id
    reqdata += '&client_secret=' + client_secret
    reqdata += '&tenant_id=' + tenant_id

    #Sends token request to Visma Connect to receive authentication-token
    response = requests.post('https://connect.visma.com/connect/token',
                             data=reqdata,
                             headers={
                                 'Content-Type': 'application/x-www-form-urlencoded'
                                }
                             )

    if response.status_code == 200:
        json_data = json.loads(response.text)

        return json_data["access_token"]

#         {
#   "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjVENDc....7MTOBbdd5mgb2CHzxL0RFjs24pqC1pCeUqOjbg",
#   "expires_in": 3600,
#   "token_type": "Bearer",
#   "scope": "visma_api:read"
# }

@app.route("/payroll/getemployees", methods=["GET"])
def getemployees():

    data, token = querydata('employees', None, None)

    employees = data

    while token != None:
        data, token = querydata('employees', None, token)
        employees.extend(data)
        pass

    return jsonify(employees)

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

@app.route("/payroll/getpaycodes", methods=["GET"])        
def getpaycodes():

    params = {
        'paycodeType': 'Time'
    }

    data, token = querydata('paycodes', params, None)

    paycodes = data

    while token != None:
        data, token = querydata('paycodes', params, token)
        paycodes.extend(data)
        pass

    return jsonify(paycodes)

def querydata(endpoint, requestparams, cursor):

    if cursor != None:
        if requestparams == None:
            requestparams = {'cursor': cursor}
        else:
            requestparams['cursor'] = cursor
           
    response = requests.get('https://api.payroll.core.hrm.visma.net/v1/query/' + endpoint,
                headers={
                    'Authorization': 'Bearer ' + gettoken(),
                    'accept': 'application/json'
                },
                params=requestparams
    )

    if response.status_code == 200:
        json_data = json.loads(response.text)

        if 'cursor' in json_data:
            nextToken = json_data['cursor']['nextToken']
        else:
            nextToken = None

        return json_data['data'], nextToken

@app.route("/payroll/createtransaction", methods=["POST"])   
def createtransaction():
    data = request.json

    positions = getpositions(data["employeeid"])

    transactiondata = {
        'paycodeId': data["paycodeid"],
        'employeeId': data["employeeid"],
        'positionId': positions[0]["id"],
        'quantity': int(data["quantity"]),
        'price': int(data["price"]),
        'activeStart': '2021-01-17',
        'activeEnd': '2021-01-17'
    }

# {
#   "id": "string",
#   "payoutPeriodDate": "2021-01-14",
#   "positionId": "string",
#   "employeeId": "string",
#   "paycodeId": "string",
#   "paycodeIdentifier": 0,
#   "factor": 0,
#   "quantity": 0,
#   "price": 0,
#   "totalPrice": 0,
#   "activeStart": "2021-01-14",
#   "activeEnd": "2021-01-14",
#   "additionalInfo": [
#     {
#       "identifier": 0,
#       "value": "string"
#     }
#   ],
#   "accountingDimensions": [
#     {
#       "identifier": "string",
#       "value": "string",
#       "percentage": 0
#     }
#   ]
# }

    response = requests.post('https://api.payroll.core.hrm.visma.net/v1/command/transaction/create',
                headers={
                    'Authorization': 'Bearer ' + gettoken(),
                    'Content-type': 'application/json'
                },
                json=transactiondata
    )

    if response.status_code == 202:
        location = response.headers['Location']
     
        jobid = location.split('/')
        jobid = jobid[len(jobid) - 1]

        return jobid

@app.route("/payroll/getjobstatus/<jobid>", methods=["GET"])   
def getjobstatus(jobid):

    response = requests.get('https://api.payroll.core.hrm.visma.net/v1/command/transaction/jobs/' + jobid,
                headers={
                    'Authorization': 'Bearer ' + gettoken(),
                    'accept': 'application/json'
                }
    )

    if response.status_code == 200:
        json_data = json.loads(response.text)

        return json_data['status']