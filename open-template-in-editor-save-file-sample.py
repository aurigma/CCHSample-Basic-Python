######################
# INSTRUCTIONS:
# -------------
# This script is organized as a simple Python-based no-dependency webserver. In the beginning you will find
# some functions used to make API calls. Next, in the `do_GET()` function of `SimpleHTTPRequestHandler` you will find HTML code which displays the editor.
# And next, in the `do_POST()` function you will find a code which converts a design created in the editor to a PDF file.
#
# To test it, login to your Customer's Canvas account, create the Integration and External App
# and add their data to the variables in the CONFIGURATION section below.
#
# After that just run it with `python3 sample.py` in a command prompt. It will start a web server at
# http://localhost:8000. Once you open it in a browser, you will see the editor. Modify the design and 
# click the **Save image to server** button.
# 
# As a result:
# 1. A PDF version of an image is saved in the same folder where you run the script.
# 2. If you login to Customer's Canvas and visit the Projects section, you will see a Project corresponding to this design. 
######################

from http.server import HTTPServer, BaseHTTPRequestHandler

from io import BytesIO

import json
import urllib3
import time

######################
# CONFIGURATION      #
######################

# Register your system in Customer's Canvas account as explained here:
# https://customerscanvas.com/dev/backoffice/storefront/creating-custom-integration.html 
storefront_id = 4242 # Insert your Storefront ID here

# In this example, we are using OAuth2 auth scheme called Client Credentials. Create an External App
# in your Customer's Canvas account and add the Client ID and Secret here.
# See more detailed: https://customerscanvas.com/dev/backoffice/auth.html 
client_id = 'Enter Client ID' 
secret = 'Enter Secret Key'

#############################################

# Add design ID here. Locate it in your account, right-click, choose Properties and copy ID.
your_design_id = 'Enter your design ID here...'

# Specify here the ID of a user in your system so that the saved results and uploads could be 
# properly stored. 
your_system_user_id = 'some_user_id_12345'

# Customer's Canvas implements its own identity server based on OAuth2 protocol. Use this address
# to request the access tokens.  
auth_url = 'https://customerscanvashub.com/connect/token'

# Customer's Canvas API Gateway address to make calls to the most of its API (except of the Design Editor Web API). 
base_api_url = 'https://api.customerscanvashub.com/'

client = urllib3.PoolManager()


##########################################################
# TASK 1. AUTHENTICATION/AUTHORIZATION                   #
##########################################################
# 
# You need to get an Access Token to make calls to Customer's Canvas API. This subject is explained in 
# more details at https://customerscanvas.com/dev/backoffice/auth.html
# 
# In short, you need to do the following
# 1. Register an External App for your application with an auth flow Client Credentials.
# 2. Specify the `client_id` and `secret` variables (see above).
# 3. Make a call to https://customerscanvashub.com/connect/token as shown in the `get_access_token()` function below.
# 4. Use the `access_token` value of the response as a part of `Authorization: Bearer <your access token>` header when sending
#    requests to Customer's Canvas API.
#
# Design Editor application is a separate app with its own backend. It also needs authentication (not based on OAuth2), 
# and you are receiving its tokens in a bit different manner:
# 1. Get API Key from your tenant settings.
# 2. Use the POST `{design_editor_url}/api/Auth/Users/{user_id}/Tokens` API to create a token.
# 3. Add it to the Design Editor configuration on the frontend along with the user ID, as explained below.
# 
# Here is a description of the Design Editor token API: 
# https://customerscanvas.com/dev/editors/design-editor-web-app/apis/auth-tokens.html
#
# HINT: A wise idea would be to organize some sort of caching of these values with extending them when they expire  
# or request new ones.

def get_access_token():
    payload = {
        'client_id': client_id, 
        'client_secret': secret, 
        'scope': 'Projects_full Tenants_read Artifacts_read', 
        'grant_type': 'client_credentials'
    }

    r = client.request_encode_body('POST', auth_url, fields=payload, encode_multipart=False)
    response_as_string = r.data.decode('utf8')
    return json.loads(response_as_string)['access_token']

def get_tenant_applications():
    r = client.request(
        'GET', 
        f'{base_api_url}/api/storefront/v1/tenant-info/applications', 
        headers={"Authorization": f"Bearer {get_access_token()}"}
    )
    response_as_string = r.data.decode('utf8')
    r.release_conn()

    return json.loads(response_as_string)

def get_design_editor_url():
    return get_tenant_applications()['designEditorUrl']

def get_design_editor_apikey():
    return get_tenant_applications()['designEditorApiKey']

def get_design_editor_token(user_id):
    base_address = get_design_editor_url() 
    api_key = get_design_editor_apikey() 
    r = client.request(
        'POST', 
        f'{base_address}/api/Auth/Users/{user_id}/Tokens', 
        headers={"X-CustomersCanvasAPIKey": f"{api_key}"}
    )
    response_as_string = r.data.decode('utf8')
    r.release_conn()

    # Use these lines of code to debug API responses
    # print("HTTP Code: {code} {reason}, length={length}".format(code=r.status, reason=r.reason, length=len(r.data)))
    # print("Response: " + response_as_string)

    return json.loads(response_as_string)["tokenId"]


def create_project(state_id, user_id, format, color_space, resolution):
    payload = {
        'ownerId': user_id,
        'name': f'PROJ-{state_id}',
        'description': f'Project for state {state_id}',
        'scenario': {
            'designId': state_id,
            'name': f'resultfile_{state_id}',
            'dpi': resolution,
            'format': format,
            'colorSpace': color_space,
            'flipMode': 'None',
            'allowAnonymous': False
        }
    }
    
    r = client.request(
        'POST', 
        f'{base_api_url}/api/storefront/v1/projects/by-scenario/render-hires?storefrontId={storefront_id}', 
        body=json.dumps(payload), 
        headers={
                "Authorization": f"Bearer {get_access_token()}",
                "Content-Type": "application/json"
            }
            )

    response_as_string = r.data.decode('utf8')
    result = json.loads(response_as_string)

    r.release_conn()
    
    return result

def check_project_results(project_id): 
    r = client.request(
        'GET', 
        f'{base_api_url}/api/storefront/v1/projects/{project_id}/processing-results', 
        headers={"Authorization": f"Bearer {get_access_token()}"})
    
    response_as_string = r.data.decode('utf8')

    # Use these lines of code to debug API responses
    # print("HTTP Code: {code} {reason}, length={length}".format(code=r.status, reason=r.reason, length=len(r.data)))
    # print("Response: " + response_as_string)

    result = json.loads(response_as_string)

    r.release_conn()
    
    return result

    
def download_file(url, filename): 
    r = client.request('GET', url, preload_content=False, headers={"Authorization": f"Bearer {get_access_token()}"})

    with open(filename, 'wb') as out:
        chunk_size = 1024*1024 
        while True:
            data = r.read(chunk_size)
            if not data:
                break
            out.write(data)

    r.release_conn()

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    ###############################################################
    # TASK 2. HOW TO OPEN THE EDITOR ON THE FRONTEND (NO DESIGN). #
    ###############################################################

    # In this case we want to open an empty Design Editor with a blank artboard of a specific size. 
    # The simplest way is to use the IFrameAPI library, described here:
    # 
    # https://customerscanvas.com/dev/editors/iframe-api/overview.html 
    #
    # In short, you need to add several elements to your HTML page:
    # 1. Add the link to IFrameAPI library of Design Editor of the version installed to your Customer's Canvas account.
    # 2. Add `<iframe>` element to the page where you want to show the editor.
    # 3. Add a button which will cause Design Editor to save the result.
    # 4. Add a script which initializes the editor by referencing to the iframe you have added.
    # 5. To make the upload functionality to work correctly, it is also necessary to provide the user ID and Design Editor token 
    #    as discussed above (as a part of the editor configuration).
    #
    # The base address of your Design Editor instance can be retrieved through API. See the `get_design_editor_url()` function
    # above.
    # 
    # When adding a script, you need also to add the `id='CcIframeApiScript'` attribute to the `<script>` tag.
    #
    # To load the editor to the `<iframe>` element, you need to call the `CustomersCanvas.IframeApi.loadEditor()` JS function.
    # It requires three params - a reference to iframe, product definition, and editor config.
    #
    # Design Editor supports various product definitions, including design ID from your Customer's Canvas account. The easiest way
    # to find a public design template ID is to locate it in an asset manager in your Customer's Canvas account, right-click, and 
    # choose Properties menu as explained here: 
    #
    # https://customerscanvas.com/help/admin-guide/manage-assets/file-manager.html#information
    #
    # In real-life applications you will either use API or extract it from the product variant or your database, however, discussing
    # these use cases is out of scope of this code example. 
    #
    # More details about product definition options can be found here: 
    # 
    # https://customerscanvas.com/dev/editors/iframe-api/product-definition/examples.html
    # (note, some of them are not relevant to the cloud installation of Customer's Canvas)
    #
    # As for the editor config, it is quite large structure. It allows for very detailed configuration of the user interface
    # (like what toolbox buttons are available, colors in the color picker, images in the gallery, etc). Learn more here:  
    # https://customerscanvas.com/dev/editors/iframe-api/editor-configuration/intro.html    
    #
    # When you are ready to save the result, you need to use the `editor.saveProduct()` method and receive the private design
    # file ID (we also call the state files). After that we pass this ID to the backend part (see below) to convert it to PDF. 

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(str.encode("""
<html>
  <head>
    <style> 
        .main__iframe {{
            height: calc(100% - 6rem);
            width: 100%;
        }}
        .main__iframe iframe {{
            border: none;
            height: 100%;
            width: 0;
            min-width: 100%;
            position: relative;
        }}
        .header {{
            padding: .85rem 1.42rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: .07rem solid #E0E0E0;
        }}

        .header__logo {{
            display: block;
        }}

        .header__button {{
            padding: .7rem;
            background: #30C2FF;
            border-radius: .21rem;
            border: none;
            font-family: Roboto;
            font-style: normal;
            font-weight: bold;
            line-height: 1.14rem;
            font-size: 1rem;
            text-align: center;
            cursor: pointer;
            color: #FFFFFF;
        }}

        .header__button:hover {{
            background: #2BAFE6;
        }}

        .header__button:focus {{
            background: #2BAFE6;
            outline: none;
        }}

        .header__button:disabled {{
            background: #DCDEDF;
            pointer-events: none;
        }}
        .main__info {{
            text-align: end;
            margin-top: .5rem;
            margin-right: .5rem;
            color: #2BAFE6;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 10px;
        }}                                    
    </style>
    <script>
        const targetSizeInInches = {{ width: 5, height: 3.5 }};
        
        const inchToPoints = (inchSize) => ({{ width: inchSize.width * 72, height: inchSize.height * 72}});
                                    

        document.addEventListener('DOMContentLoaded', async () => {{
            let product = "{design_id}"; 

            let config = {{
                  userId: "{user_id}",
                  tokenId: "{design_editor_token}",
                  initialMode: "Advanced",
                  canvas: {{
                    shadowEnabled: true
                  }}                  
            }};
            document.getElementById('version-box').innerText = 'version ' + CustomersCanvas.VERSION;

            // Customer's Canvas is loaded with this line. See the JSON objects above for params.
            var editor = await CustomersCanvas.IframeApi.loadEditor(
                document.getElementById('editorFrame'), product, config);
            
            // Now the editor is ready. Let's enabled the Save button.
            document.getElementById('finish').removeAttribute("disabled");

            document.getElementById('finish').addEventListener('click', async () => {{
                const result = await editor.saveProduct();
                const saveImageEndpointUrl = "."; // the same as this page, use your backend address here.
                await fetch(
                    saveImageEndpointUrl, 
                    {{ 
                        method: 'POST', 
                        headers: {{
                            "Content-Type": "application/json"
                        }},
                        body: JSON.stringify({{ stateId: result.stateId, userId: result. userId}}) 
                    }});
                alert("The design with id " + result.stateId + " is saved as PDF on the server");
            }});
        }});
    </script>
  </head>
  <body>
    <header class="header">
        <div class="header__section header__section-logo">
            <a href="https://customerscanvas.com/" target="_blank" class="header__logo">
                <img src="https://customerscanvas.com/Aurigma/Theme5/img/logo.svg" />
            </a>
        </div>
        <div class="header__section header__section-button">
            <button class="header__button" id="finish"
                    disabled="disabled">
                Save image to server
            </button>
        </div>
    </header>
    <div class='main__iframe'><iframe id='editorFrame'></iframe></div>
    <p class='main__info' id='version-box'></p>

    <script type='text/javascript' id='CcIframeApiScript' src='{design_editor_url}/Resources/Generated/IframeApi.js'>
    </script>
  </body>
</html>
""".format(
        user_id=your_system_user_id, 
        design_editor_token=get_design_editor_token(your_system_user_id), 
        design_editor_url=get_design_editor_url(),
        design_id=your_design_id)))

    ###############################################################
    # TASK 3. HOW TO CONVERT DESIGN FILE (AKA STATE FILE) TO PDF  #
    ###############################################################

    # General idea is described in this article: 
    # https://customerscanvas.com/dev/backoffice/howto/processing-personalization-results.html?tabs=curl
    #    
    # In short:
    # 1. We need to get the ID of a design created by the user.
    # 2. We need to create a Project in Customer's Canvas. When it happens, it runs the rendering process.
    # 3. We need to wait the rendering to be finished.
    # 4. When it happens, we need to download the result file and use it in the way you need. In the purpose 
    #    of this code example, we will just save it to the same folder with the script. 

    def do_POST(self):
        
        # From the frontend we will receive the ID of a design file created by the user as well as the user id.
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        body_as_string = body.decode('utf8')

        state_id = json.loads(body_as_string)['stateId']
        user_id = json.loads(body_as_string)['userId']

        # This function is declared above. It creates a project in Customer's Canvas and runs a built-in 
        # rendering pipeline. Here you pass some settings, like output file format and resolution. 
        project = create_project(state_id, user_id, "Pdf", "Cmyk", 300)
        
        # Note, the rendering process run asyncronously. For lightweight designs it should be finished
        # almost immediately, but some slight delays still may happen. That's why you need to implement 
        # polling mechanism - check a project status, if it is still Pending, wait for few seconds and try again.
        # Don't forget to limit a number of retries to prevent endless loop in case if something goes wrong.

        isPending = True
        isSuccess = False
        failureDetails = ''
        counter = 0

        while isPending and counter < 20: 
            time.sleep(3)

            # This function is declared above. It receives an object called "processing results".
            # It includes a status = Pending | InProgress | Completed | Failed. In case
            # of status = Completed, it also includes file details (potentially, a rendering pipeline may 
            # create multiple files, however, in our case it will be only one file).   
            project_results = check_project_results(project["id"])
            project_status = project_results["status"]

            if project_status == "Completed":

                file_details = project_results["outputFileDetails"]
                for result_info in file_details:
                    # This function is declared above. It downloads a file from the url
                    # and saves it as a file. It assumes that you download it from Customer's Canvas
                    # and adds the Authorization header with a token.
                    download_file(result_info["url"], f'{result_info["name"]}.pdf')

                isPending = False
                isSuccess = True

            elif project_status == "Failed":
                # If the rendering pipeline fails, you can see the error details. 
                # Alternatively, you can sign in to Customer's Canvas account, find the 
                # project there, and see the rendering pipeline run report.
                failureDetails = project_results.statusDescription

                isPending = False
                isSuccess = False

            # other options are project_results.status == "InProgress" or "Pending" 
            # we will loop again with isPending = True
            counter += 1

        if isSuccess:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = BytesIO()
            response.write(b'Successfully saved a file.')
        else: 
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = BytesIO()
            response.write(b'Failed to render a file.')
            response.write(str.encode(failureDetails))

        self.wfile.write(response.getvalue())


httpd = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
httpd.serve_forever()