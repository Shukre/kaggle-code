import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelBinarizer

import gc
import time


####
# load the data
####
print('reading in data')

all_train = pd.read_csv('./data/train_cleaned.csv')
#all_train.head() 

final_test = pd.read_csv('./data/test_cleaned.csv')
#final_test.head()

raw_test = pd.read_csv('./data/test.csv')

submission = pd.read_csv('./data/sample_submission.csv')
#submission.head()


####
# check submission length
####

#it is lower than the number of ids in the test set?
len(submission['fullVisitorId']) == len(set(submission['fullVisitorId']))
len(set(submission['fullVisitorId'])) == len(set(final_test['fullVisitorId']))
len(submission['fullVisitorId']) ==  len(set(final_test['fullVisitorId']))

unaccounted = [x for x in submission['fullVisitorId'] if x not in final_test['fullVisitorId'] ]
len(unaccounted)
for i, x in enumerate(submission['fullVisitorId']):
	try:
		int(x)
	except:
		print(i, x)
#there are 
for i, x in enumerate(final_test['fullVisitorId']):
	try:
		int(x)
	except:
		print(i, x)


len(raw_test['fullVisitorId']) == len(final_test['fullVisitorId'])

"""
####
# explore what we are looking at
####

#need to go through and clean the columns
all_train.describe()

all_train.columns
#51 columns
all_train['adwordsClickInfo'][0] #this is still json buy okay
type(all_train['transactionRevenue'][0])  == np.float64#this is the one we are trying to predict
all_train.columns
"""

####
# scan columns and classify
####

numeric = []
categorical = []
flatline = []
other = []

for col in all_train.columns:
	if type(all_train[col][0]) == str:
		#categorical
		if len(all_train[col].unique()) > 1:
			categorical.append(col)
		else:
			flatline.append(col)
	elif type(all_train[col][0]) == int or type(all_train[col][0]) == np.float64:
		#numeric
		numeric.append(col)
	else:
		other.append(col)

numeric
categorical
flatline
other

####
# other columns
####
drop_other = ['visitId',
				'campaignCode',
				'referralPath',
				'adwordsClickInfo',
				'adContent']


numeric_other = ['visitNumber', 
					'hits',
					'visits']

categorical_other = ['isMobile',]



####
# drop flat cols for both the train and test data
####

flatline.extend(drop_other)
#should drop the flatline columns from the df
all_train = all_train.drop(flatline, axis = 1)
all_train.shape

flatline = [x for x in flatline if x != 'campaignCode' ]
final_test = final_test.drop(flatline, axis=1)
final_test.shape

for i in list(all_train.columns):
	if i not in list(final_test.columns):
		print(i)


#######
# finish cleaning the columns
#######
all_train.head()
final_test.head()


####
# numeric
####
print('numeric variables')

#'fullVisitorId' #removed form numeric, this is just the id
#'transactionRevenue' #this is the response variable we want to predict

numeric = [ 'newVisits',
			 'pageviews',
			 'transactionRevenue',
			 ]

numeric.extend(numeric_other)

all_train['transactionRevenue'].fillna(0, inplace = True)

def fill_and_adj_numeric(df):
	#there are NA for page views, fill median for this == 1
	df.pageviews.fillna(df.pageviews.median(), inplace = True)

	df.hits.fillna(df.hits.median(), inplace = True)
	df.visits.fillna(df.visits.median(), inplace = True)

	#are boolean, fill NaN with zeros, add to categorical
	df.isTrueDirect.fillna(0, inplace = True)
	df.bounces.fillna(0, inplace = True)
	df.newVisits.fillna(0, inplace = True)
	df.visitNumber.fillna(1, inplace = True)

	for col in ['isTrueDirect', 'bounces', 'newVisits']:
		df[col] = df[col].astype(int)

	return df

all_train = fill_and_adj_numeric(all_train)
final_test = fill_and_adj_numeric(final_test)


####
# datetime columns
##
print('Date variable')
all_train['date'] #this needs to be processed with datetime

def parseDateCol(df, date_col):
	""" takes the date column and adds new columns with the features:
		yr, mon, day, day of week, day of year """
	df['datetime'] = df.apply(lambda x : time.strptime(str(x[date_col]),  "%Y%M%d"), axis = 1)
	print('parsing year')
	df['year'] = df.apply(lambda x : x['datetime'].tm_year, axis = 1)
	print('parsing month')
	df['month'] = df.apply(lambda x :x['datetime'].tm_mon , axis = 1)
	print('parsing days (*3 versions)')
	df['mday'] = df.apply(lambda x : x['datetime'].tm_mday, axis = 1)
	df['wday'] = df.apply(lambda x : x['datetime'].tm_wday , axis = 1)
	df['yday'] = df.apply(lambda x : x['datetime'].tm_yday , axis = 1)

	#drop date and datetime
	df = df.drop([date_col, 'datetime'], axis = 1)
	
	return df

all_train = parseDateCol(all_train, 'date')

final_test = parseDateCol(final_test, 'date')



####
# categorical
####
print('Cleaning categorical variables')

categorical = ['channelGrouping',
				 'sessionId',
				 'browser',
				 'deviceCategory',
				 'operatingSystem',
				 'city',
				 'continent',
				 'country',
				 'metro',
				 'networkDomain',
				 'region',
				 'subContinent',
				 'campaign',
				 'keyword',
				 'medium',
				 'source']

categorical.extend(categorical_other)


with_na = []
for col in categorical:
	if all_train[col].isnull().any() :
		with_na.append(col)		


####
# fill na for all the categoricals with the 'None' if string or mode if bool
####

#most common value to fill the na
all_train.keyword.fillna('(not provided)', inplace = True)

def binarize_col(train, test, col):
	encoder = LabelBinarizer()

	cat_train_1hot = encoder.fit_transform(train[col])
	
	cat_test_1hot = encoder.transform(test[col])

	return cat_train_1hot, cat_test_1hot


train_bins = []
test_bins = []
#this is crashing... need a little more memory I think
for col in categorical:
	if len(all_train[col].unique()) > 1 and len(all_train[col].unique()) < 500:

		print(f'binarizing:{col}\tunique: {len(all_train[col].unique())}')

		bin_col_all_train, bin_col_final_test = binarize_col(all_train, final_test, col)

		if len(train_bins) == 0:
			print('initializing np matrix')
			train_bins = bin_col_all_train	
			test_bins =	bin_col_final_test
		else:
			print('appending to np matrix')
			train_bins = np.c_[train_bins, bin_col_all_train]
			test_bins = np.c_[test_bins, bin_col_final_test]
	gc.collect()

train_bins.shape
test_bins.shape


#drop the non binarized categorical columns and the housekeeping ones ones to the 
#the train and test sets for sklearn

all_train = all_train.drop(categorical, axis = 1)
final_test = final_test.drop(categorical, axis = 1)


# isolate the response variable
y_train = all_train['transactionRevenue'].values


all_train.columns

for x in all_train.columns:
	print(x, all_train[x].dtype)


X_train = all_train.drop(['fullVisitorId','transactionRevenue'], axis = 1).values
X_train = np.c_[X_train, train_bins]
X_train.shape


X_test = final_test.drop(['fullVisitorId'], axis = 1).values
X_test = np.c_[X_test, test_bins]
X_test.shape

#TODO: try pickling the data instead of writing to file!

#X_train.dump('X_train.dat')
#y_train.dump('y_train.dat')
#X_test.dump('X_test.dat')



