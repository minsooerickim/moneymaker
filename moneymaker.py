import ccxt
import pandas as pd
pd.set_option('display.max_rows', None)
import warnings
warnings.filterwarnings('ignore')
from utility import bcolors

exchange = ccxt.coinbasepro({
    "apiKey": 'api_key',
    "secret": 'secret',
    'password':'password'
})
       
def tr(data):
    data['previous_close'] = data['close'].shift(1)
    data['high-low'] = abs(data['high'] - data['low'])
    data['high-pc'] = abs(data['high'] - data['previous_close'])
    data['low-pc'] = abs(data['low'] - data['previous_close'])

    tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)

    return tr

def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()

    return atr

def supertrend(df, period=2, atr_multiplier=1):
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period)
    df['upperband'] = hl2 + (atr_multiplier * df['atr'])
    df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
    df['in_uptrend'] = True
    for current in range(2, len(df.index)+1):
        previous = current - 1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]
    # print(df)
    return df


in_position = False

def check_buy_sell_signals(df, amount):
    global in_position
    # print(df)
    # print(df.tail(3))

    # print("checking for buy and sell signals")
    last_row_index = len(df.index) 
    previous_row_index = last_row_index - 1
    if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
        if not in_position:
            print(f"{bcolors.OKGREEN} changed to uptrend, buy")
            try:
                order = exchange.create_market_buy_order('ETH/USDT', amount)
                print(f'{bcolors.OKGREEN} PURCHASED!')
                print(order)
                in_position = True
            except:
                pass
        # else:
            # print("already in position, nothing to do")
    
    if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
        if in_position:
            print(f'{bcolors.FAIL} changed to downtrend, sell')
            try:
                order = exchange.create_market_sell_order('ETH/USDT', amount)
                print(f'{bcolors.FAIL} SOLD')
                print(order)
                in_position = False
            except:
                pass
        # else:
            # print("You aren't in position, nothing to sell")

def run_bot(amount):
    # print(f"Fetching new bars for {datetime.now().isoformat()}")
    bars = exchange.fetch_ohlcv('ETH/USDT', timeframe='5m', limit=100)
    
    df1 = pd.DataFrame(bars[:-1], columns=['timestamps', 'open', 'high', 'low', 'close', 'volume'])
    df1['timestamps'] = pd.to_datetime(df1['timestamps'], unit='ms')
    df1 = df1.loc[:,['timestamps', 'open', 'high', 'low', 'close']]
    

    df = df1[['timestamps','open','close','high','low']].copy()
    for i in range(df.shape[0]):
        if i > 0:
            df.loc[df.index[i],'open'] = (df1['open'][i-1] + df1['close'][i-1])/2
    
        df.loc[df.index[i],'close'] = (df1['open'][i] + df1['close'][i] + df1['low'][i] +  df1['high'][i])/4
    df = df.iloc[1:,:]
    supertrend_data = supertrend(df)
    
    check_buy_sell_signals(supertrend_data, amount)

if __name__ == '__main__':
    print("MAKE SURE YOU HAVE SUFFICIENT USDT TO MAKE THE TRANSACTION")
    print('time to make some money boiiiii')
    amount= float(input("Enter the ETH you want to trade with: "))
    print(f'{bcolors.OKGREEN} \nTrading with {amount} ETH')
    while True:
        run_bot(amount)
