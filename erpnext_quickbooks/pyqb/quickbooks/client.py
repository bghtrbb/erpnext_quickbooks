try:  # Python 3
    import http.client as httplib
    from urllib.parse import parse_qsl
except ImportError:  # Python 2
    import httplib
    from urlparse import parse_qsl

from .exceptions import QuickbooksException, SevereException

try:
    from rauth import OAuth2Session, OAuth2Service
except ImportError:
    print("Please import Rauth:\n\n")
    print("http://rauth.readthedocs.org/en/latest/\n")
    raise
import json


class QuickBooks(object):
    """A wrapper class around Python's Rauth module for Quickbooks the API"""

    access_token = ''
    access_token_key = ''
    client_id = ''
    client_secret = ''
    company_id = 0
    realm_id = 0
    callback_url = ''
    session = None
    sandbox = False
    minorversion = None
    scope = 'com.intuit.quickbooks.accounting'
    response_type = 'code'
    state = 'NONE'

    qbService = None

    sandbox_api_url_v3 = "https://sandbox-quickbooks.api.intuit.com/v3"
    api_url_v3 = "https://quickbooks.api.intuit.com/v3"

    access_token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

    authorize_url = "https://appcenter.intuit.com/connect/oauth2"

    request_token = ''
    request_token_secret = ''

    _BUSINESS_OBJECTS = [
        "Account", "Attachable", "Bill", "BillPayment",
        "Class", "CompanyInfo", "CreditMemo", "Customer",
        "Department", "Employee", "Estimate", "Invoice",
        "Item", "JournalEntry", "Payment", "PaymentMethod",
        "Preferences", "Purchase", "PurchaseOrder",
        "SalesReceipt", "TaxCode", "TaxRate", "Term",
        "TimeActivity", "Vendor", "VendorCredit"
    ]

    __instance = None

    def __new__(cls, **kwargs):
        if QuickBooks.__instance is None:
            QuickBooks.__instance = object.__new__(cls)

        if 'client_id' in kwargs:
            cls.client_id = kwargs['client_id']

        if 'client_secret' in kwargs:
            cls.client_secret = kwargs['client_secret']

        if 'access_token' in kwargs:
            cls.access_token = kwargs['access_token']

        if 'access_token_key' in kwargs:
            cls.access_token_key = kwargs['access_token_key']

        if 'company_id' in kwargs:
            cls.company_id = kwargs['company_id']

        if 'callback_url' in kwargs:
            cls.callback_url = kwargs['callback_url']

        if 'sandbox' in kwargs:
            cls.sandbox = kwargs['sandbox']

        if 'minorversion' in kwargs:
            cls.minorversion = kwargs['minorversion']

        return QuickBooks.__instance

    @classmethod
    def get_instance(cls):
        return cls.__instance

    def _drop(self):
        QuickBooks.__instance = None

    @property
    def api_url(self):
        if self.sandbox:
            return self.sandbox_api_url_v3
        else:
            return self.api_url_v3

    def create_session(self):
        if self.client_secret and self.client_id and self.access_token_key and self.access_token:
            session = OAuth2Session(
                client_id = self.client_id,
                client_secret = self.client_secret,
                access_token = self.access_token
            )
            self.session = session
        else:
            raise QuickbooksException("Quickbooks authenication fields not set. Cannot create session.")

        return self.session

    def get_authorize_url(self):
        """
        Returns the Authorize URL as returned by QB.
        :return URI:
        """
        if self.qbService is None:
            self.set_up_service()

        auth_url = self.qbService.get_authorize_url()+'&scope='+self.scope+'&redirect_uri='+self.callback_url+'&response_type='+self.response_type+'&state='+self.state
        return auth_url

    def set_up_service(self):
        self.qbService = OAuth2Service(
            name=None,
            client_id=self.client_id,
            client_secret=self.client_secret,
            access_token_url=self.access_token_url,
            authorize_url=self.authorize_url,
            base_url=None
        )

    def get_access_tokens(self, code):
        """
        Wrapper around get_auth_session, returns session, and sets access_token and
        access_token_key on the QB Object.
        """

        # create a dictionary for the data we'll post on the get_access_token request
        data = dict(code=code, redirect_uri=self.callback_url,grant_type='authorization_code')

        # retrieve the authenticated session
        token = self.qbService.get_access_token(decoder=json.loads, data=data)

        session = self.qbService.get_session(token)

        self.access_token = token

        return session


    def make_request(self, request_type, url, request_body=None, content_type='application/json'):

        params = {}

        if self.minorversion:
            params['minorversion'] = self.minorversion
        print "params",type (params), params 

        if not request_body:
            request_body = {}

        if self.session is None:
            self.create_session()

        headers = {
            'Content-Type': content_type,
            'Accept': 'application/json'
        }

        req = self.session.request(request_type, url, True, self.company_id, headers=headers, params=params, data=request_body)

        try:
            result = req.json()
        except:
            raise QuickbooksException("Error reading json response: {0}".format(req.text), 10000)

        if req.status_code is not httplib.OK or "Fault" in result:
            self.handle_exceptions(result["Fault"])
        else:
            return result

    def make_request_query(self, request_type, url, request_body=None, content_type='application/json'):

        params = {}
        if self.minorversion:
            params['minorversion'] = self.minorversion
        params['query'] =  request_body

        print "params",type (params), params ,type (params['query'])
        if not request_body:
            request_body = {}

        if self.session is None:
            self.create_session()

        headers = {
            'Content-Type': content_type,
            'Accept': 'application/json'
        }
        
        req = self.session.request(request_type, url, True, str(self.company_id), headers=headers, params=params)
        # req = self.session.request(request_type, url, True, self.company_id, headers=headers, params=params, data=request_body)
        
        try:
            result = req.json()
        except:
            raise QuickbooksException("Error reading json response: {0}".format(req.text), 10000)

        if req.status_code is not httplib.OK or "Fault" in result:
            self.handle_exceptions(result["Fault"])
        else:
            return result

    def get_single_object(self, qbbo, pk):
        url = self.api_url + "/company/{0}/{1}/{2}/".format(self.company_id, qbbo.lower(), pk)
        result = self.make_request_query("GET", url, {})

        return result

    def handle_exceptions(self, results):
        # Needs to handle multiple errors
        for error in results["Error"]:

            message = error["Message"]

            detail = ""
            if "Detail" in error:
                detail = error["Detail"]

            code = ""
            if "code" in error:
                code = int(error["code"])

            if code >= 10000:
                raise SevereException(message, code, detail)
            else:
                raise QuickbooksException(message, code, detail)

    def create_object(self, qbbo, request_body):
        self.isvalid_object_name(qbbo)

        url = self.api_url + "/company/{0}/{1}".format(self.company_id, qbbo.lower())
        results = self.make_request("POST", url, request_body)
        print results
        return results

    def query(self, select):
        url = self.api_url + "/company/{0}/query".format(self.company_id)
        result = self.make_request_query("POST", url, select, content_type='text/plain')
        return result

    def isvalid_object_name(self, object_name):
        if object_name not in self._BUSINESS_OBJECTS:
            raise Exception("{0} is not a valid QBO Business Object.".format(object_name))

        return True

    def update_object(self, qbbo, request_body):
        url = self.api_url + "/company/{0}/{1}".format(self.company_id, qbbo.lower())
        result = self.make_request("POST", url, request_body)

        return result

    def batch_operation(self, request_body):
        url = self.api_url + "/company/{0}/batch".format(self.company_id)
        results = self.make_request("POST", url, request_body)
        return results

    def download_pdf(self, qbbo, item_id):
        url = self.api_url + "/company/{0}/{1}/{2}/pdf".format(self.company_id, qbbo.lower(), item_id)

        if self.session is None:
            self.create_session()

        headers = {
            'Content-Type': 'application/pdf',
            'Accept': 'application/pdf, application/json',
        }

        response = self.session.request("GET", url, True, self.company_id, headers=headers)

        if response.status_code is not httplib.OK:
            try:
                json = response.json()
            except:
                raise QuickbooksException("Error reading json response: {0}".format(response.text), 10000)
            self.handle_exceptions(json["Fault"])
        else:
            return response.content