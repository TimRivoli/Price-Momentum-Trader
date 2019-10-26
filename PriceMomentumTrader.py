import pandas as pd
import datetime, sys
from _classes.PriceTradeAnalyzer import TradingModel, PricingData, StockPicker, GetTodaysDate
from _classes.TickerLists import TickerLists

def TodaysRecommendations(tickerList:str, stockCount:int=9, currentDate:str='', longHistoryDays:int=365, shortHistoryDays:int=90, filterOption:int=3, NoFilter:bool=False, minPercentGain=0.05):
	if currentDate =='':  currentDate = GetTodaysDate()
	currentDate = datetime.datetime.strptime(currentDate, '%m/%d/%Y')
	picker = StockPicker()
	for t in tickerList:
		picker.AddTicker(t)
	shortList = picker.GetHighestPriceMomentum(currentDate=currentDate, longHistoryDays=longHistoryDays, shortHistoryDays=shortHistoryDays, stocksToReturn=stockCount, filterOption=filterOption, minPercentGain=minPercentGain)
	print('Today''s recommendations', currentDate)
	print(shortList)
	shortList.to_csv('data/TodaysPicks.csv')

def RunBuyHold(ticker: str, startDate:datetime, durationInYears:int, ReEvaluationInterval:int=20, portfolioSize:int=30000, verbose:bool=False):
	modelName = 'BuyHold_' + (ticker) + '_' + startDate[-4:]
	tm = TradingModel(modelName=modelName, startingTicker=ticker, startDate=startDate, durationInYears=durationInYears, totalFunds=portfolioSize, traunchSize=portfolioSize/10, verbose=verbose)
	if not tm.modelReady:
		print('Unable to initialize price history for model BuyHold date ' + str(startDate))
		return 0
	else:
		dayCounter =0
		while not tm.ModelCompleted():
			if dayCounter ==0:
				tm.SellAllPositions(tm.currentDate)
				i=0
				while tm.TraunchesAvailable() and i < 10000: 
					tm.PlaceBuy(ticker=ticker, price=1, marketOrder=True, expireAfterDays=10, verbose=verbose)
					i  +=1
			dayCounter+=1
			if dayCounter >= ReEvaluationInterval: dayCounter=0
			tm.ProcessDay()
		cash, asset = tm.Value()
		print('Ending Value: ', cash + asset, '(Cash', cash, ', Asset', asset, ')')
		return tm.CloseModel(plotResults=False, saveHistoryToFile=verbose)	

def RunPriceMomentum(tickerList:list, startDate:str='1/1/1982', durationInYears:int=36, stockCount:int=9, ReEvaluationInterval:int=20, filterOption:int=3, longHistory:int=365, shortHistory:int=90, minPercentGain=0.05, maxVolatility=.12, portfolioSize:int=30000, returndailyValues:bool=False, verbose:bool=False):
	#Choose the stock with the greatest long term (longHistory days) price appreciation
	#shortHistory is a shorter time frame (like 90 days) used differently by different filters
	#ReEvaluationInterval is how often to re-evaluate our choices, ideally this should be very short and not matter, otherwise the date selection is biased.
	startDate = datetime.datetime.strptime(startDate, '%m/%d/%Y')
	endDate =  startDate + datetime.timedelta(days=365 * durationInYears)
	picker = StockPicker(startDate, endDate)
	for t in tickerList:
		picker.AddTicker(t)
	tm = TradingModel(modelName='PriceMomentumShort_longHistory_' + str(longHistory) +'_shortHistory_' + str(shortHistory) + '_reeval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) + '_filter' + str(filterOption) + '_' + str(minPercentGain) + str(maxVolatility), startingTicker='^SPX', startDate=startDate, durationInYears=durationInYears, totalFunds=portfolioSize, traunchSize=portfolioSize/stockCount, verbose=verbose)
	dayCounter = 0
	if not tm.modelReady:
		print('Unable to initialize price history for PriceMomentum date ' + str(startDate))
		return 0
	else:
		while not tm.ModelCompleted():
			currentDate =  tm.currentDate
			if dayCounter ==0:
				print('\n')
				print(currentDate)
				c, a = tm.Value()
				print(tm.modelName, int(c), int(a), int(c+a))
				print('available/buy/sell/long',tm.PositionSummary())
				tm.SellAllPositions(currentDate)
				tm.ProcessDay()
				dayCounter+=1
				shortList = picker.GetHighestPriceMomentum(currentDate, longHistoryDays=longHistory, shortHistoryDays=shortHistory, stocksToReturn=stockCount, filterOption=filterOption, minPercentGain=minPercentGain, maxVolatility=maxVolatility)
				shortList = shortList[:stockCount]
				print(shortList)
				if len(shortList) > 0:
					i=0
					ii=0
					while tm.TraunchesAvailable() and i < 100: #Over long periods 100 will not be enough, 1000 would be better, but 100 also limits the impact of early gains, after a bit you are trading $300K
						tm.PlaceBuy(ticker=shortList.index[ii], price=1, marketOrder=True, expireAfterDays=10, verbose=verbose)
						i  +=1
						ii +=1
						if ii >= len(shortList): ii=0
			tm.ProcessDay()
			dayCounter+=1
			if dayCounter >= ReEvaluationInterval: dayCounter=0

		cv1 = tm.CloseModel(plotResults=False, saveHistoryToFile=((durationInYears>1) or verbose))
		if returndailyValues:
			return tm.GetDailyValue()
		else:
			return cv1
	
def RunPriceMomentumBlended(tickerList:list, startDate:str='1/1/1980', durationInYears:int=29, stockCount:int=9,  ReEvaluationInterval:int=20, longHistory:int=365, shortHistory:int=90, portfolioSize:int=30000, returndailyValues:bool=False, verbose:bool=False):
	#Uses blended option for selecting stocks using three different filters
	startDate = datetime.datetime.strptime(startDate, '%m/%d/%Y')
	endDate =  startDate + datetime.timedelta(days=365 * durationInYears)
	picker = StockPicker(startDate, endDate)
	for t in tickerList:
		picker.AddTicker(t)
	tm = TradingModel(modelName='PriceMomentum_Blended_longHistory_' + str(longHistory) +'_shortHistory_' + str(shortHistory) + '_reeval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) + '_filterBlended_134', startingTicker='^SPX', startDate=startDate, durationInYears=durationInYears, totalFunds=portfolioSize, traunchSize=portfolioSize/stockCount, verbose=verbose)
	dayCounter = 0
	if not tm.modelReady:
		print('Unable to initialize price history for PriceMomentum date ' + str(startDate))
		return 0
	else:
		while not tm.ModelCompleted():
			currentDate =  tm.currentDate
			if dayCounter ==0:
				print('\n')
				print(currentDate)
				c, a = tm.Value()
				print(tm.modelName, int(c), int(a), int(c+a))
				print('available/buy/sell/long',tm.PositionSummary())
				tm.SellAllPositions(currentDate)
				tm.ProcessDay()
				dayCounter+=1
				shortList1 = picker.GetHighestPriceMomentum(currentDate, longHistoryDays=longHistory, shortHistoryDays=shortHistory, stocksToReturn=int(stockCount/3), filterOption=1)
				shortList2 = picker.GetHighestPriceMomentum(currentDate, longHistoryDays=longHistory, shortHistoryDays=shortHistory, stocksToReturn=int(stockCount/3), filterOption=2)
				shortList3 = picker.GetHighestPriceMomentum(currentDate, longHistoryDays=longHistory, shortHistoryDays=shortHistory, stocksToReturn=int(stockCount/3), filterOption=4)
				#shortList3 = picker.GetHighestPriceMomentum(currentDate, longHistoryDays=longHistory, shortHistoryDays=shortHistory, stocksToReturn=int(stockCount/3), filterOption=6, maxVolatility=.12)
				shortList = pd.concat([shortList1, shortList2, shortList3])
				shortList
				print(shortList)
				if len(shortList) > 0:
					i=0
					ii=0
					while tm.TraunchesAvailable() and i < 100: 
						tm.PlaceBuy(ticker=shortList.index[ii], price=1, marketOrder=True, expireAfterDays=10, verbose=verbose)
						i  +=1
						ii +=1
						if ii >= len(shortList): ii=0
			tm.ProcessDay()
			dayCounter+=1
			if dayCounter >= ReEvaluationInterval: dayCounter=0

		cv1 = tm.CloseModel(plotResults=False, saveHistoryToFile=((durationInYears>1) or verbose))
		if returndailyValues:
			return tm.GetDailyValue()
		else:
			return cv1

def ComparePMToBH(startYear:int=1982, endYear:int=2018, durationInYears:int=6, stockCount:int=5, ReEvaluationInterval:int=20, filterOption:int=3, longHistory:int=365, shortHistory:int=90):
	modelOneName = 'BuyHold'
	modelTwoName = 'PriceMomentum_longHistory_' + str(longHistory) +'_shortHistory_' + str(shortHistory) + '_ReEval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) + '_filter' + str(filterOption)
	portfolioSize=30000
	TestResults = pd.DataFrame(columns=list(['StartDate','Duration', modelOneName + 'EndingValue', modelTwoName + 'EndingValue', modelOneName + 'Gain', modelTwoName + 'Gain', 'Difference']))
	TestResults.set_index(['StartDate'], inplace=True)		
	trials = int((endYear - startYear)/durationInYears) 
	for i in range(trials):
		startDate = '1/2/' + str(startYear + i * durationInYears)
		m1ev = RunBuyHold('^SPX', startDate=startDate, durationInYears=durationInYears, ReEvaluationInterval=ReEvaluationInterval, portfolioSize=portfolioSize)
		m2ev = RunPriceMomentum(tickerList = TickerLists.SPTop70(), startDate=startDate, durationInYears=durationInYears, stockCount=stockCount, ReEvaluationInterval=ReEvaluationInterval, filterOption=filterOption,  longHistory=longHistory, shortHistory=shortHistory, portfolioSize=portfolioSize, returndailyValues=False, verbose=False)
		m1pg = (m1ev/portfolioSize) - 1 
		m2pg = (m2ev/portfolioSize) - 1
		TestResults.loc[startDate] = [durationInYears, m1ev, m2ev, m1pg, m2pg, m2pg-m1pg]
	TestResults.to_csv('data/trademodel/Compare' + modelOneName + '_to_' + modelTwoName + '_year ' + str(startYear) + '_duration' + str(durationInYears) +'.csv')
	print(TestResults)

def CompareBlendedToBH(startYear:int=1982, endYear:int=2018, durationInYears:int = 6, stockCount:int=5, ReEvaluationInterval:int=20, longHistory:int=365, shortHistory:int=90):
	modelOneName = 'BuyHold'
	modelTwoName = 'PriceMomentumBlended_longHistory_' + str(longHistory) +'_shortHistory_' + str(shortHistory) + '_ReEval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) + '_filterBlended'
	portfolioSize=30000
	TestResults = pd.DataFrame(columns=list(['StartDate','Duration', modelOneName + 'EndingValue', modelTwoName + 'EndingValue', modelOneName + 'Gain', modelTwoName + 'Gain', 'Difference']))
	TestResults.set_index(['StartDate'], inplace=True)		
	trials = int((endYear - startYear)/durationInYears) 
	for i in range(trials):
		startDate = '1/2/' + str(startYear + i * durationInYears)
		m1ev = RunBuyHold('^SPX', startDate=startDate, durationInYears=durationInYears, ReEvaluationInterval=ReEvaluationInterval, portfolioSize=portfolioSize)
		m2ev = RunPriceMomentumBlended(tickerList = TickerLists.SPTop70(), startDate=startDate, durationInYears=durationInYears, stockCount=stockCount, ReEvaluationInterval=ReEvaluationInterval, longHistory=longHistory, shortHistory=shortHistory, portfolioSize=portfolioSize, returndailyValues=False, verbose=False)
		m1pg = (m1ev/portfolioSize) - 1 
		m2pg = (m2ev/portfolioSize) - 1
		TestResults.loc[startDate] = [durationInYears, m1ev, m2ev, m1pg, m2pg, m2pg-m1pg]
	TestResults.to_csv('data/trademodel/Compare' + modelOneName + '_to_' + modelTwoName + '_year ' + str(startYear) + '_duration' + str(durationInYears) +'.csv')
	print(TestResults)
	
if __name__ == '__main__':
	switch = 0
	if len(sys.argv[1:]) > 0: switch = sys.argv[1:][0]
	tickers = TickerLists.SPTop70()
	print('Running default option on ' + str(len(tickers)) + ' stocks.')
	RunPriceMomentum(tickerList = tickers, startDate='1/1/1982', durationInYears=36, stockCount=9, ReEvaluationInterval=30, filterOption=2, longHistory=365, shortHistory=45) 
	RunPriceMomentum(tickerList = tickers, startDate='1/1/1982', durationInYears=36, stockCount=5, ReEvaluationInterval=30, filterOption=2, longHistory=365, shortHistory=45) 
	RunPriceMomentum(tickerList = tickers, startDate='1/1/1982', durationInYears=36, stockCount=2, ReEvaluationInterval=30, filterOption=2, longHistory=365, shortHistory=45) 
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=9, filterOption=4, longHistory=365, shortHistory=90) 
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=5, filterOption=4, longHistory=365, shortHistory=90) 
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=2, filterOption=4, longHistory=365, shortHistory=90) 
	TodaysRecommendations(tickerList=tickers, stockCount=100, currentDate='', minPercentGain=.05, filterOption=2)
