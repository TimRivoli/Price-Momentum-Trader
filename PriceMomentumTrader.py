import sys
import pandas as pd
from _classes.PriceTradeAnalyzer import TradingModel, PricingData, StockPicker
from _classes.TickerLists import TickerLists
from _classes.Utility import *

def RunBuyHold(ticker: str, startDate:str, durationInYears:int, ReEvaluationInterval:int=20, portfolioSize:int=30000, verbose:bool=False):
	#Baseline model to compare against.  Buy on day one, hold for the duration and then sell
	modelName = 'BuyHold_' + (ticker) + '_' + startDate[-4:]
	tm = TradingModel(modelName=modelName, startingTicker=ticker, startDate=startDate, durationInYears=durationInYears, totalFunds=portfolioSize, tranchSize=portfolioSize/10, verbose=verbose)
	if not tm.modelReady:
		print('Unable to initialize price history for model BuyHold date ' + str(startDate))
		return 0
	else:
		dayCounter =0
		while not tm.ModelCompleted():
			if dayCounter ==0:
				i=0
				while tm.TranchesAvailable() and i < 100: 
					tm.PlaceBuy(ticker=ticker, price=1, marketOrder=True, expireAfterDays=10, verbose=verbose)
					i +=1
			dayCounter+=1
			if dayCounter >= ReEvaluationInterval: dayCounter=0
			tm.ProcessDay()
		cash, asset = tm.Value()
		print('Ending Value: ', cash + asset, '(Cash', cash, ', Asset', asset, ')')
		return tm.CloseModel(plotResults=False, saveHistoryToFile=verbose)	

def RunPriceMomentum(tickerList:list, startDate:str='1/1/1982', durationInYears:int=36, stockCount:int=9, ReEvaluationInterval:int=20, filterOption:int=3, longHistory:int=365, shortHistory:int=90, minPercentGain=0.05, portfolioSize:int=30000, returndailyValues:bool=False, verbose:bool=False):
	#Choose stockCount stocks with the greatest long term (longHistory days) price appreciation, using different filter options defined in the StockPicker class
	#shortHistory is a shorter time frame (like 90 days) used differently by different filters
	#ReEvaluationInterval is how often to re-evaluate our choices, ideally this should be very short and not matter, otherwise the date selection is biased.
	allocateByPointValue=True
	startDate = ToDate(startDate)
	endDate =  AddDays(startDate, 365 * durationInYears)
	picker = StockPicker(AddDays(startDate, -730), endDate) #Include earlier dates for statistics
	for t in tickerList:
		picker.AddTicker(t)
	tm = TradingModel(modelName='PriceMomentumShort_longHistory_' + str(longHistory) +'_shortHistory_' + str(shortHistory) + '_reeval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) + '_filter' + str(filterOption) + '_' + str(minPercentGain), startingTicker='.INX', startDate=startDate, durationInYears=durationInYears, totalFunds=portfolioSize, tranchSize=portfolioSize/stockCount, verbose=verbose)
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
				candidates = picker.GetHighestPriceMomentum(currentDate, longHistoryDays=longHistory, shortHistoryDays=shortHistory, stocksToReturn=stockCount, filterOption=filterOption, minPercentGain=minPercentGain)
				if allocateByPointValue:
					print('Allocating by point value')
					candidates = pd.DataFrame(candidates.groupby(['Ticker'])['Point_Value'].sum()) #Group by ticker, sum Point_Value and call that TargetHoldings
					candidates.rename(columns={'Point_Value':'TargetHoldings'}, inplace=True)
				else:
					print('Allocating evenly')
					candidates = pd.DataFrame(candidates.groupby(['Ticker']).size()) #Group by ticker with new colum for TargetHoldings, .size=count; .sum=sum, keeps only the index and the count
					candidates.rename(columns={0:'TargetHoldings'}, inplace=True)
				tm.AlignPositions(targetPositions=candidates)
			tm.ProcessDay()
			dayCounter+=1
			if dayCounter >= ReEvaluationInterval: dayCounter=0

		cv1 = tm.CloseModel(plotResults=False, saveHistoryToFile=((durationInYears>1) or verbose))
		if returndailyValues:
			return tm.GetDailyValue()
		else:
			return cv1
			
def ComparePMToBH(startYear:int=1982, endYear:int=2018, durationInYears:int=1, stockCount:int=9, ReEvaluationInterval:int=20, filterOption:int=3, longHistory:int=365, shortHistory:int=90):
	#Compares the PriceMomentum strategy to BuyHold in one year intervals, outputs the returns to .csv file
	modelOneName = 'BuyHold'
	modelTwoName = 'PriceMomentum_longHistory_' + str(longHistory) +'_shortHistory_' + str(shortHistory) + '_ReEval_' + str(ReEvaluationInterval) + '_stockcount_' + str(stockCount) + '_filter' + str(filterOption)
	portfolioSize=30000
	TestResults = pd.DataFrame(columns=list(['StartDate','Duration', modelOneName + 'EndingValue',  'ModelEndingValue', modelOneName + 'Gain', 'ModelGain', 'Difference']))
	TestResults.set_index(['StartDate'], inplace=True)		
	trials = int((endYear - startYear)/durationInYears) 
	for i in range(trials):
		startDate = '1/2/' + str(startYear + i * durationInYears)
		m1ev = RunBuyHold('.INX', startDate=startDate, durationInYears=durationInYears, ReEvaluationInterval=ReEvaluationInterval, portfolioSize=portfolioSize)
		m2ev = RunPriceMomentum(tickerList = TickerLists.AllTopPerformers(), startDate=startDate, durationInYears=durationInYears, stockCount=stockCount, ReEvaluationInterval=ReEvaluationInterval, filterOption=filterOption,  longHistory=longHistory, shortHistory=shortHistory, portfolioSize=portfolioSize, returndailyValues=False, verbose=False)
		m1pg = (m1ev/portfolioSize) - 1 
		m2pg = (m2ev/portfolioSize) - 1
		TestResults.loc[startDate] = [durationInYears, m1ev, m2ev, m1pg, m2pg, m2pg-m1pg]
	TestResults.sort_values(['Difference'], axis=0, ascending=True, inplace=True)
	TestResults.to_csv('data/trademodel/Compare' + modelOneName + '_to_' + modelTwoName + '_year ' + str(startYear) + '_duration' + str(durationInYears) +'.csv')
	print(TestResults)

def ExtensiveTesting1():
	#Helper subroutine for running multiple tests
	RunPriceMomentum(tickerList = tickers, startDate='1/1/1982', durationInYears=36, stockCount=5, ReEvaluationInterval=20, filterOption=2, longHistory=365, shortHistory=30) 
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=9, filterOption=3, longHistory=365, shortHistory=90) 

def ExtensiveTesting2():
	#Helper subroutine for running multiple tests
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=9, filterOption=2, longHistory=120, shortHistory=90) 
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=9, filterOption=2, longHistory=180, shortHistory=90) 
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=9, filterOption=2, longHistory=240, shortHistory=90) 

def ExtensiveTesting3():
	#Helper subroutine for running multiple tests
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=9, filterOption=1, longHistory=365, shortHistory=90) 
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=9, filterOption=3, longHistory=365, shortHistory=90) 
	ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=9, filterOption=4, longHistory=365, shortHistory=90) 
	
def ModelPastYear():
	#Show how each strategy performs on the past years data
	startDate = AddDays(GetTodaysDate(), -370)
	RunPriceMomentum(tickerList = tickers, startDate=startDate, durationInYears=1, stockCount=5, ReEvaluationInterval=20, verbose=True)
	RunBuyHold(ticker='.INX', startDate=startDate, durationInYears=1)

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
	elif switch == '4':
		print('Running option: ', switch)
		ModelPastYear()
	else:
		tickers = TickerLists.SPTop70()
		print('Running default option on ' + str(len(tickers)) + ' stocks.')
		RunBuyHold('.INX', startDate='1/1/2000', durationInYears=10, ReEvaluationInterval=5, portfolioSize=30000, verbose=False)	#Baseline
		RunPriceMomentum(tickerList = tickers, startDate='1/1/2000', durationInYears=10, stockCount=5, ReEvaluationInterval=20, filterOption=4, longHistory=365, shortHistory=90) #Shows how the strategy works over a long time period
		ComparePMToBH(startYear=2000,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=5, filterOption=1, longHistory=365, shortHistory=60) #Runs the model in one year intervals, comparing each to BuyHold
		#ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=5, filterOption=2, longHistory=365, shortHistory=60) #Runs the model in one year intervals, comparing each to BuyHold
		#ComparePMToBH(startYear=1982,endYear=2018, durationInYears=1, ReEvaluationInterval=20, stockCount=5, filterOption=4, longHistory=365, shortHistory=60) #Runs the model in one year intervals, comparing each to BuyHold
