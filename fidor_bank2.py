from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect, session, url_for, render_template
from requests.auth import HTTPBasicAuth
import requests
import json
import os
from prettytable import PrettyTable
from requests import Request, Session


from flask import Flask, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pusher import Pusher
import requests, json, atexit, time, plotly, plotly.graph_objs as go

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'de517b15255cbf77a26e0c3be6d6c328'
client_id = "00f3c6c36ec984f7"
client_secret = "de517b15255cbf77a26e0c3be6d6c328"

authorization_base_url = 'https://apm.tp.sandbox.fidor.com/oauth/authorize'
token_url = 'https://apm.tp.sandbox.fidor.com/oauth/token'
redirect_uri = 'http://localhost:5000/callback'

@app.route('/', methods=["GET"])
@app.route('/index', methods=["GET"])
def default():
    fidor = OAuth2Session(client_id,redirect_uri=redirect_uri)
    authorization_url, state = fidor.authorization_url(authorization_base_url)
    session['oauth_state'] = state
    print("authorization URL is =" +authorization_url)
    return redirect(authorization_url)

@app.route("/callback", methods=["GET"])
def callback():
    fidor = OAuth2Session(state=session['oauth_state'])
    authorizationCode = request.args.get('code')
    body = 'grant_type="authorization_code&code='+authorizationCode+ \
    '&redirect_uri='+redirect_uri+'&client_id='+client_id
    auth = HTTPBasicAuth(client_id, client_secret)
    token = fidor.fetch_token(token_url,auth=auth,code=authorizationCode,body=body,method='POST')

    session['oauth_token'] = token
    return redirect(url_for('.services'))

@app.route("/services", methods=["GET"])
def services():
    try:
        token =  session['oauth_token']  
        url = "https://api.tp.sandbox.fidor.com/accounts"

        payload = ""
        headers = {
            'Accept': "application/vnd.fidor.de;version=1;text/json",
            'Authorization': "Bearer "+token["access_token"],
            'cache-control': "no-cache",
            'Postman-Token': "91920a7d-d9f9-4e93-b03f-66f65da75468"
            }

        response = requests.request("GET", url, data=payload, headers=headers)
        print("services=" + response.text)
        customersAccount = json.loads(response.text)
        customerDetails = customersAccount['data'][0]
        customerInformation = customerDetails['customers'][0] 
        session['fidor_customer'] = customersAccount

        return render_template('services.html',fID=customerInformation["id"],
                fFirstName=customerInformation["first_name"],fLastName=customerInformation["last_name"],
                fAccountNo=customerDetails["account_number"],fBalance=(customerDetails["balance"]/100))

    except KeyError:
        print("Key error in services-to return back to index")
        return redirect(url_for('default'))

@app.route("/bank_transfer", methods=["GET"])
def transfer():
    try:
        customersAccount = session['fidor_customer']
        customerDetails = customersAccount['data'][0]

        return render_template('internal_transfer.html',fFIDORID=customerDetails["id"],
            fAccountNo=customerDetails["account_number"],fBalance=(customerDetails["balance"]/100))

    except KeyError:
        print("Key error in bank_transfer-to return back to index")
        return redirect(url_for('.index'))


@app.route("/process", methods=["POST"])
def process():

    if request.method == "POST":
        token =  session['oauth_token']         
        customersAccount = session['fidor_customer']
        customerDetails = customersAccount['data'][0]

        fidorID = customerDetails['id']
        custEmail = request.form['customerEmailAdd']
        transferAmt = int(float(request.form['transferAmount'])*100)
        transferRemarks = request.form['transferRemarks']
        transactionID = request.form['transactionID']

        url = "https://api.tp.sandbox.fidor.com/internal_transfers"

        payload = "{\n\t\"account_id\": \""+fidorID+"\",\n\t\"receiver\": \""+ \
                custEmail+"\",\n\t\"external_uid\": \""+transactionID+"\",\n\t\"amount\": "+ \
                str(transferAmt)+",\n\t\"subject\": \""+transferRemarks+"\"\n}\n"

        headers = {
            'Accept': "application/vnd.fidor.de; version=1,text/json",
            'Authorization': "Bearer "+token["access_token"],
            'Content-Type': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "6dc13ce9-5e6e-4ff6-bd7c-82508356c3a1"
            }

        response = requests.request("POST", url, data=payload, headers=headers)

        print("process="+response.text)

        transactionDetails = json.loads(response.text)
        return render_template('transfer_result.html',fTransactionID=transactionDetails["id"],
                custEmail=transactionDetails["receiver"],fRemarks=transactionDetails["subject"],
                famount=(float(transactionDetails["amount"])/100),
                fRecipientName=transactionDetails["recipient_name"])

# @app.route("/startpage")
# def start_page():
#     return render_template('startpage.html')

@app.route("/login")
def login():
    return render_template('login.html')

@app.route('/stock',methods=['GET'])
def stock():
    return render_template('stock.html')

@app.route('/result',methods=['GET','POST'])
def result():
    error = None
    if request.method == "POST":
        tickerCode = request.form['stockSymbol']
        api_key = request.form['APIKey']

        url = "https://www.alphavantage.co/query"

        querystring = {"function":"DIGITAL_CURRENCY_DAILY","symbol":tickerCode,"market":"SGD","apikey":api_key}

        payload = ""
        headers = {
            'cache-control': "no-cache",
            'Postman-Token': "a3bbc02c-e94a-4ab3-a421-e98d0ff2a147"
            }

        response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

        stockData = json.loads(response.content)
        lastRefreshedDate = stockData["Meta Data"]["6. Last Refreshed"]
        lastestStockPrices = stockData["Time Series (Digital Currency Daily)"][lastRefreshedDate.split(" ")[0]]
        closingPrice = lastestStockPrices["4a. close (SGD)"]
        volume = lastestStockPrices["5. volume"]
    
    return render_template('stock_price.html',tCode=tickerCode,
            sPrice=closingPrice,cVolume=volume,dTime=lastRefreshedDate)




pusher = Pusher(
    app_id='909511',
    key='b490ed1a673cab9eb2e2',
    secret='8535980f9a8653a532cd',
    cluster='ap1',
    ssl=True
)
times = []
currencies = ["BTC"]
prices = {"BTC": []}

@app.route('/chart',methods=['GET'])
def index():
    return render_template("chart.html")

def retrieve_data():
    current_prices = {}
    for currency in currencies:
        current_prices[currency] = []
    times.append(time.strftime('%H:%M:%S'))

    api_url = "https://min-api.cryptocompare.com/data/pricemulti?fsyms={}&tsyms=USD".format(",".join(currencies))
    response = json.loads(requests.get(api_url).content)

    for currency in currencies:
        price = response[currency]['USD']
        current_prices[currency] = price
        prices[currency].append(price)

    graph_data = [go.Scatter(
        x=times,
        y=prices.get(currency),
        name="{} Prices".format(currency)
        ) for currency in currencies]

    bar_chart_data = [go.Bar(
        x=currencies,
        y=list(current_prices.values())
        )]

    data = {
        'graph': json.dumps(list(graph_data), cls=plotly.utils.PlotlyJSONEncoder),
        'bar_chart': json.dumps(list(bar_chart_data), cls=plotly.utils.PlotlyJSONEncoder)
    }

    pusher.trigger("crypto", "data-updated", data)

scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    func=retrieve_data,
    trigger=IntervalTrigger(seconds=10),
    id='prices_retrieval_job',
    name='Retrieve prices every 10 seconds',
    replace_existing=True)
atexit.register(lambda: scheduler.shutdown())







@app.route('/startpage',methods=['GET'])
def start_page():

    url = 'https://min-api.cryptocompare.com/data/v2/news/?lang=EN'
    parameters = {
    'categoties':'BTC, ETH, ETC'
    }
    headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': '603bddb407b0b5e4cec38f7837adf4c4f437a1093dbe6fda915e1929951cd23e',
    }

    session = Session()
    session.headers.update(headers)

    response = session.get(url, params=parameters)
    data = json.loads(response.text)
    print(data)

    response = requests.request("GET", url, headers=headers)

    newsData = json.loads(response.content)
    newsContent = newsData["Data"]
    newsTitle = newsContent[0]["title"]
    newsBody = newsContent[0]["body"]
    newsImage = newsContent[0]["imageurl"]
   
    newsTitle1 = newsContent[1]["title"]
    newsBody1 = newsContent[1]["body"]
    newsImage1 = newsContent[1]["imageurl"]

    newsTitle2 = newsContent[2]["title"]
    newsBody2 = newsContent[2]["body"]
    newsImage2 = newsContent[2]["imageurl"]

    newsTitle3 = newsContent[3]["title"]
    newsBody3 = newsContent[3]["body"]
    newsImage3 = newsContent[3]["imageurl"]

    

    return render_template('startpage.html',nTitle=newsTitle,nBody=newsBody,nImage=newsImage,
                                            nTitle1=newsTitle1,nBody1=newsBody1,nImage1=newsImage1,
                                            nTitle2=newsTitle2,nBody2=newsBody2,nImage2=newsImage2,
                                            nTitle3=newsTitle3,nBody3=newsBody3,nImage3=newsImage3)


@app.route("/history", methods=["GET"])
def history():

        token =  session['oauth_token']  
        url = "https://api.tp.sandbox.fidor.com/transactions"

        payload = ""
        headers = {
            'Accept': "application/vnd.fidor.de;version=1;text/json",
            'Content-Type': "application/x-www-form-urlencoded",
            'Authorization': "Bearer "+token["access_token"],
            'cache-control': "no-cache",
            'Postman-Token': "91920a7d-d9f9-4e93-b03f-66f65da75468"
            }

        response = requests.request("GET", url, data=payload, headers=headers)
        data = json.loads(response.text)
        print(data)
    
        historyData = json.loads(response.content)
        historyContent = historyData["data"]
        transactionType = historyContent[0]['transaction_type']
        amount = historyContent[0]['amount']
        detail = historyContent[0]["transaction_type_details"]
        receiver = detail["remote_name"]
        recipient = detail['recipient']

        transactionType1 = historyContent[1]['transaction_type']
        amount1 = historyContent[1]['amount']
        detail1 = historyContent[1]["transaction_type_details"]
        receiver1 = detail1["remote_name"]
        recipient1 = detail1['recipient']

        transactionType2 = historyContent[2]['transaction_type']
        amount2 = historyContent[2]['amount']
        detail2 = historyContent[2]["transaction_type_details"]
        receiver2 = detail2["remote_name"]
        recipient2 = detail2['recipient']

        transactionType3 = historyContent[3]['transaction_type']
        amount3 = historyContent[3]['amount']
        detail3 = historyContent[3]["transaction_type_details"]
        receiver3 = detail3["remote_name"]
        recipient3 = detail3["recipient"]


        return render_template('history.html',type=transactionType, am=amount, receive=receiver, email=recipient,
                                              type1=transactionType1, am1=amount1, receive1=receiver1, email1=recipient1,
                                              type2=transactionType2, am2=amount2, receive2=receiver2, email2=recipient2,
                                              type3=transactionType3, am3=amount3, receive3=receiver3, email3=recipient3)


