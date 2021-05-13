from flask import Flask, render_template, redirect, url_for, request
import requests
import json

app = Flask(__name__)
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

        querystring = {"function":"TIME_SERIES_INTRADAY","symbol":tickerCode,"interval":"5min","apikey":api_key}

        payload = ""
        headers = {
            'cache-control': "no-cache",
            'Postman-Token': "10b636d3-6e76-4352-ba6d-2601169694da"
            }

        response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

        #convert from JSON string to Python Dictionary
        stockData = json.loads(response.text)
        #To retrieve the latest date from Meta Data
        lastRefreshedDate = stockData["Meta Data"]["3. Last Refreshed"]
        #To retrieve lastest stock price
        latestStockPrices = stockData["Time Series (5min)"][lastRefreshedDate]
        #closingPrice = latestStockPrices["4. close"]
        closingPrice = stockData["Time Series (5min)"][ "2019-01-14 14:45:00"]["4. close"]
        #volume = latestStockPrices["5. volume"]
        volume = stockData["Time Series (5min)"][ "2019-01-14 14:45:00"]["5. volume"]
        

    return render_template('stock_price.html',tCode=tickerCode,
            sPrice=closingPrice,cVolume=volume,dTime=lastRefreshedDate)

