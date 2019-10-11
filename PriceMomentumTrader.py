import pandas as pd
import datetime, sys
from _classes.PriceTradeAnalyzer import TradingModel, PricingData, StockPicker, GetTodaysDate
from _classes.TickerLists import TickerLists

def RunBuyHold(ticker: str, startDate:datetime, durationInYears:int, portfolioSize:int=30000, verbose:bool=False):
	modelName = 'BuyHold_' + (ticker) + '_' + startDate[-4:]
	tm = TradingModel(modelName=modelName, startingTicker=ticker, startDate=startDate, durationInYears=durationInYears, totalFunds=portfolioSize, traunchSize=portfolioSize)
	if not tm.modelReady:
		print('Unable to initialize price history for model BuyHold date ' + str(startDate))
		return 0
	else:
		tm.PlaceBuy(ticker=ticker, price=1, marketOrder=True, expireAfterDays=10, verbose=verbose)
		while not tm.ModelCompleted():
			tm.ProcessDay()
		cash, asset = tm.Value()
		print('Ending Value: ', cash + asset, '(Cash', cash, ', Asset', asset, ')')
		return tm.CloseModel(plotResults=False, saveHistoryToFile=verbose)	

def RunBuyHoldList(tickerList:list, startDate:datetime, durationInYears:int, portfolioSize:int=30000, verbose:bool=False):
	c = len(tickerList)
	modelName = 'BuyHold_tickerList_count' + str(c) + '_' + startDate[-4:]
	tm = TradingModel(modelName=modelName, startingTicker=tickerList[0], startDate=startDate, durationInYears=durationInYears, totalFunds=portfolioSize, traunchSize=portfolioSize/c)
	if not tm.modelReady:
		print('Unable to initialize price history for BuyHoldList date ' + str(startDate))
		return 0
	else:
		for t in tickerList:
			tm.PlaceBuy(ticker=t, price=1, marketOrder=True, expireAfterDays=10, verbose=verbose)
		while not tm.ModelCompleted():
			tm.ProcessDay()
		cash, asset = tm.Value()
		print('Ending Value: ', cash + asset, '(Cash', cash, ', Asset', asset, ')')
		return tm.CloseModel(plotResults=False, saveHistoryToFile=verbose)	


def RunPriceMomentum(tickerList:list, startDate:str='1/1/1980', durationInYears:int=29,  lookBack:int=365, ReEvaluationInterval:int=20, stockCount:int=10, filterOption:int=3, portfolioSize:int=30000, returndailyValues:bool=False, verbose:bool=False):
	#Choose the stock with the greatest long term price momentum 
	#lookBack: days to look back to determine long term performance, ReEvaluationInterval: days before positions are re-evaluated and short term performance
	startDate = datetime.datetime.strptime(startDate, '%m/%d/%Y')
	endDate =  startDate + datetime.timedelta(days=365 * durationInYears)
	picker = StockPicker(startDate, endDate)
	for t in tickerList:
		picker.AddTicker(t)
	tm = TradingModel(modelName='PriceMomentum_lookBack_' + str(lookBack) +'_reeval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) + '_filter' + str(filterOption), startingTicker='^SPX', startDate=startDate, durationInYears=durationInYears, totalFunds=portfolioSize, traunchSize=portfolioSize/stockCount, verbose=verbose)
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
				shortList = picker.GetHighestPriceMomentum(currentDate, lookBack, ReEvaluationInterval, stockCount, filterOption)
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
	
def RunPriceMomentumBlended(tickerList:list, startDate:str='1/1/1980', durationInYears:int=29,  ReEvaluationInterval:int=10, stockCount:int=9, portfolioSize:int=30000, returndailyValues:bool=False, verbose:bool=False):
	#Choose the stock with the greatest long term price momentum 
	#lookBack: days to look back to determine long term performance, ReEvaluationInterval: days before positions are re-evaluated and short term performance
	#Uses blended option for selecting stocks
	lookBack=365
	startDate = datetime.datetime.strptime(startDate, '%m/%d/%Y')
	endDate =  startDate + datetime.timedelta(days=365 * durationInYears)
	picker = StockPicker(startDate, endDate)
	for t in tickerList:
		picker.AddTicker(t)
	tm = TradingModel(modelName='PriceMomentum_Blended_reeval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount), startingTicker='^SPX', startDate=startDate, durationInYears=durationInYears, totalFunds=portfolioSize, traunchSize=portfolioSize/stockCount, verbose=verbose)
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
				shortList1 = picker.GetHighestPriceMomentum(currentDate, lookBack, 40, int(stockCount/2), 1)
				shortList2 = picker.GetHighestPriceMomentum(currentDate, lookBack, 20, int(stockCount/2), 3)
				shortList3 = picker.GetHighestPriceMomentum(currentDate, lookBack, 40, int(stockCount/2), 3)
				shortList = pd.concat([shortList1, shortList2, shortList3])
				print(shortList1)
				print(shortList2)
				print(shortList3)
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

def TodaysRecommendations(tickerList:str, stockCount:int=9, currentDate:str='', longHistoryDays:int=365, shortHistoryDays:int=30, NoFilter:bool=False):
	if currentDate =='':  currentDate = GetTodaysDate()
	currentDate = datetime.datetime.strptime(currentDate, '%m/%d/%Y')
	filterOption=3
	if NoFilter: filterOption=0
	picker = StockPicker()
	for t in tickerList:
		picker.AddTicker(t)
	shortList = picker.GetHighestPriceMomentum(currentDate=currentDate, longHistoryDays=longHistoryDays, shortHistoryDays=shortHistoryDays, stocksToReturn=stockCount, filterOption=filterOption)
	print('Today''s recommendations', currentDate)
	print(shortList)
	shortList.to_csv('data/TodaysPicks.csv')

def TodaysRecommendations3(tickerList:str, stockCount:int=9, currentDate:str=''):
    #return stockCount stocks built from the list from three equal sets
	#1) high performers (at least 5% per year), recently at a discount or slowing down but not negative when looking at 40 days
	#2) high performers (at least 5% per year), but not negative when looking at the past 20 days
	#3) high performers (at least 5% per year), but not negative when looking at the past 40 days

	if currentDate =='':  currentDate = GetTodaysDate()
	currentDate = datetime.datetime.strptime(currentDate, '%m/%d/%Y')
	picker = StockPicker()
	for t in tickerList:
		picker.AddTicker(t)
	shortList1 = picker.GetHighestPriceMomentum(currentDate=currentDate, longHistoryDays=365, shortHistoryDays=40, stocksToReturn=int(stockCount/2), filterOption=1)
	shortList2 = picker.GetHighestPriceMomentum(currentDate=currentDate, longHistoryDays=365, shortHistoryDays=20, stocksToReturn=int(stockCount/2), filterOption=3)
	shortList3 = picker.GetHighestPriceMomentum(currentDate=currentDate, longHistoryDays=365, shortHistoryDays=40, stocksToReturn=int(stockCount/2), filterOption=3)
	shortList = pd.concat([shortList1, shortList2, shortList3])
	shortList = shortList[:stockCount]
	print('Today''s recommendations', currentDate)
	print(shortList)
	shortList.to_csv('data/TodaysPicks.csv')

def ComparePMToBH(startYear:int=1982, endYear:int=2018, durationInYears:int = 6, lookBack:int=365, ReEvaluationInterval:int=20, stockCount:int=5, filterOption:int=3):
	modelOneName = 'BuyHold'
	modelTwoName = 'PriceMomentum_lookBack_' + str(lookBack) +'_reeval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) + '_filter' + str(filterOption)
	portfolioSize=30000
	TestResults = pd.DataFrame(columns=list(['StartDate','Duration', modelOneName + 'EndingValue', modelTwoName + 'EndingValue', modelOneName + 'Gain', modelTwoName + 'Gain', 'Difference']))
	TestResults.set_index(['StartDate'], inplace=True)		
	trials = int((endYear - startYear)/durationInYears) 
	for i in range(trials):
		startDate = '1/2/' + str(startYear + i * durationInYears)
		m1ev = RunBuyHold('^SPX', startDate=startDate, durationInYears=durationInYears, portfolioSize=portfolioSize)
		m2ev = RunPriceMomentum(tickerList = TickerLists.SPTop70(), startDate=startDate, durationInYears=durationInYears, ReEvaluationInterval=ReEvaluationInterval, stockCount=stockCount, portfolioSize=portfolioSize, returndailyValues=False, verbose=False)
		m1pg = (m1ev/portfolioSize) - 1 
		m2pg = (m2ev/portfolioSize) - 1
		TestResults.loc[startDate] = [durationInYears, m1ev, m2ev, m1pg, m2pg, m2pg-m1pg]
	TestResults.to_csv('data/trademodel/Compare' + modelOneName + '_to_' + modelTwoName + '_year ' + str(startYear) + '_duration' + str(durationInYears) +'.csv')
	print(TestResults)
		
def CompareBlendedToPM(startYear:int=1982, endYear:int=2018, durationInYears:int = 6, lookBack:int=365, ReEvaluationInterval:int=20, stockCount:int=5, filterOption:int=3):
	modelOneName = 'PriceMomentum'
	modelTwoName = 'PriceMomentumBlended_lookBack_' + str(lookBack) +'_reeval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) + '_filter' + str(filterOption)
	portfolioSize=30000
	TestResults = pd.DataFrame(columns=list(['StartDate','Duration', modelOneName + 'EndingValue', modelTwoName + 'EndingValue', modelOneName + 'Gain', modelTwoName + 'Gain', 'Difference']))
	TestResults.set_index(['StartDate'], inplace=True)		
	trials = int((endYear - startYear)/durationInYears) 
	for i in range(trials):
		startDate = '1/2/' + str(startYear + i * durationInYears)
		m1ev = RunPriceMomentum(tickerList = TickerLists.SPTop70(), startDate=startDate, durationInYears=durationInYears, lookBack=lookBack, ReEvaluationInterval=ReEvaluationInterval, stockCount=stockCount, portfolioSize=portfolioSize, filterOption=filterOption, returndailyValues=False, verbose=False)
		m2ev = RunPriceMomentumBlended(tickerList = TickerLists.SPTop70(), startDate=startDate, durationInYears=durationInYears, ReEvaluationInterval=ReEvaluationInterval, stockCount=stockCount, portfolioSize=portfolioSize, returndailyValues=False, verbose=False)
		m1pg = (m1ev/portfolioSize) - 1 
		m2pg = (m2ev/portfolioSize) - 1
		TestResults.loc[startDate] = [durationInYears, m1ev, m2ev, m1pg, m2pg, m2pg-m1pg]
	TestResults.to_csv('data/trademodel/Compare' + modelOneName + '_to_' + modelTwoName + '_year ' + str(startYear) + '_duration' + str(durationInYears) +'.csv')
	print(TestResults)

def CompareBlendedToBH(startYear:int=1982, endYear:int=2018, durationInYears:int = 6, lookBack:int=365, ReEvaluationInterval:int=20, stockCount:int=5):
	modelOneName = 'BuyHold'
	modelTwoName = 'PriceMomentumBlended_lookBack_' + str(lookBack) +'_reeval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) 
	portfolioSize=30000
	TestResults = pd.DataFrame(columns=list(['StartDate','Duration', modelOneName + 'EndingValue', modelTwoName + 'EndingValue', modelOneName + 'Gain', modelTwoName + 'Gain', 'Difference']))
	TestResults.set_index(['StartDate'], inplace=True)		
	trials = int((endYear - startYear)/durationInYears) 
	for i in range(trials):
		startDate = '1/2/' + str(startYear + i * durationInYears)
		m1ev = RunBuyHold('^SPX', startDate=startDate, durationInYears=durationInYears, portfolioSize=portfolioSize)
		m2ev = RunPriceMomentumBlended(tickerList = TickerLists.SPTop70(), startDate=startDate, durationInYears=durationInYears, ReEvaluationInterval=ReEvaluationInterval, stockCount=stockCount, portfolioSize=portfolioSize, returndailyValues=False, verbose=False)
		m1pg = (m1ev/portfolioSize) - 1 
		m2pg = (m2ev/portfolioSize) - 1
		TestResults.loc[startDate] = [durationInYears, m1ev, m2ev, m1pg, m2pg, m2pg-m1pg]
	TestResults.to_csv('data/trademodel/Compare' + modelOneName + '_to_' + modelTwoName + '_year ' + str(startYear) + '_duration' + str(durationInYears) +'.csv')
	print(TestResults)

def ExtensiveTesting1():
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=90, stockCount=9) 
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=90, stockCount=5) 
	CompareBlendedToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=90, stockCount=9) 

def ExtensiveTesting2():
	CompareBlendedToBH(startYear=1995,endYear=2018, durationInYears=1, ReEvaluationInterval=90, stockCount=9) 
	CompareBlendedToBH(startYear=1995,endYear=2018, durationInYears=1, ReEvaluationInterval=120, stockCount=9) 

def ExtensiveTesting3():
	CompareBlendedToBH(startYear=1995,endYear=2018, durationInYears=1, ReEvaluationInterval=30, stockCount=9) 
	CompareBlendedToBH(startYear=1995,endYear=2018, durationInYears=1, ReEvaluationInterval=55, stockCount=9) 
	CompareBlendedToBH(startYear=1995,endYear=2018, durationInYears=1, ReEvaluationInterval=70, stockCount=9) 


if __name__ == '__main__':
	switch = 0
	if len(sys.argv[1:]) > 0: switch = sys.argv[1:][0]
	tickers = TickerLists.SPTop70()
	if switch == '1':
		print('Running option: ', switch)
		ExtensiveTesting1()
	elif switch == '2':
		print('Running option: ', switch)
		ExtensiveTesting2()
	elif switch == '3':
		print('Running option: ', switch)
		ExtensiveTesting3()
	else:
		print('Running default option.')
		RunBuyHold('^SPX', startDate='1/1/1982', durationInYears=35, portfolioSize=30000, verbose=True)
		RunPriceMomentum(tickerList = tickers, startDate='1/1/1982', durationInYears=36, ReEvaluationInterval=90, stockCount=5) 
		RunPriceMomentum(tickerList = tickers, startDate='1/1/1982', durationInYears=36, ReEvaluationInterval=90, stockCount=9) 
		TodaysRecommendations(tickerList=tickers, stockCount=9)
		
