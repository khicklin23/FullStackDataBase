import mysql.connector
import requests 
from bs4 import BeautifulSoup as bs 
import pandas as pd 
import csv
from tkinter import messagebox
import tkinter.messagebox
import customtkinter
import datetime
import random


#Connect To Database

mydb = mysql.connector.connect(
host="localhost",
user="root",
password = "", 
database="stocks"
)

mycursor = mydb.cursor()






#Grab information for all 503 S&P 500 companies

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies#S&P_500_component_stocks"
response = requests.get(url)
html_content = response.content
soup = bs(html_content, 'html.parser')
table = soup.find('table', {'class': 'wikitable sortable'})
data = [] 
rows = table.find_all('tr')
for row in rows[1:]: 
    columns = row.find_all('td')
    columns = [column.text.strip() for column in columns]
    data.append(columns)
    

#Conver to dataframe and insert into .csv

columns = ["Symbol", "sName", "GICS Sector", "GICS Sub-Industry", "Headquarters", "IPO", "stockID", "Founded"]
df = pd.DataFrame(data, columns=columns)
df_sorted = df.sort_values(by="sName")
df.to_csv('wikipedia.csv', index=False)  


#Grab Price Of Specific Stock / Sector Given Ticker Symbol

def get_price(symbol):
    url = f'https://www.google.com/search?q=${symbol}+price'  
    html = requests.get(url)
    soup = bs(html.text, 'html.parser')
    price_element = soup.find('div', class_='BNeawe iBp4i AP7Wnd')
    
    if price_element:
        price = price_element.text
        price = price.split()
        return price
    else:
        return "Price not found"
    

#Initialization of database tables in MySql

def createTables(cursor):
    
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS Stocks (
                symbol VARCHAR(10) PRIMARY KEY,
                sName VARCHAR(255),
                GICS_Sector VARCHAR(255),
                GICS_Sub_Industry VARCHAR(255),
                Headquarters VARCHAR(255),
                IPO DATE,
                stockID VARCHAR(20),
                Founded INT
            )
        """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                userID INT PRIMARY KEY,
                userName VARCHAR(16),
                password VARCHAR(16),
                amount FLOAT,
                buying_power FLOAT
            )
        """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transID INT PRIMARY KEY AUTO_INCREMENT,
                symbol VARCHAR(10),
                price FLOAT,
                shares INT,
                value FLOAT,
                sale VARCHAR(4),
                userID INT,
                datetime DATETIME,
                FOREIGN KEY (userID) REFERENCES Users(userID)
            )
        """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                posID INT NOT NULL AUTO_INCREMENT,
                symbol VARCHAR(4) NULL,
                POS FLOAT,
                shares INT NULL,
                userID INT,  
                PRIMARY KEY (posID),
                FOREIGN KEY (userID) REFERENCES Users (userID)
            )
        """)
    
#createTables(mycursor

#Insert data from .csv into the MySql Database

def insert_data_from_csv(mydb, filename):
    cursor = mydb.cursor()
    try:
        with open(filename, 'r') as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader)  # Skip first 
            for row in csvreader:
                symbol, sName, gics_sector, gics_sub_industry, headquarters, IPO, stockID, founded = row
                
                founded = int(founded.split('(')[0].strip()[:4])
                sql = "INSERT INTO Stocks (Symbol, sName, GICS_Sector, GICS_Sub_Industry, Headquarters, IPO, stockID, Founded) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                val = (symbol, sName, gics_sector, gics_sub_industry, headquarters, IPO, stockID, founded)
                cursor.execute(sql, val)
            mydb.commit()
            print("Data inserted successfully.")
    except Exception as e:
        #Doesnt break the database if there is an error in inserting data
        print("Error inserting data:", e)
        mydb.rollback()
    finally:
        cursor.close()

filename = 'wikipedia.csv'
#insert_data_from_csv(mydb, filename)





#Function to view all stocks and information in stocks table

def viewStockTable():
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM Stocks")
    items = cursor.fetchall()
    if not items:
        print("No data found in the Stocks table.")
        return
    print("Stocks Table:")
    for row in items:
        print(row)
    cursor.close()



#Function to clear all database data (full wipe)

def clearUsers(cursor):
    cursor.execute("DELETE FROM positions")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM Users")
    mydb.commit()


#Sector Dictionary

sectorID = {
    'Industrials': 'XLI',
    'Technology': 'XLK',
    'Utilities': 'XLU',
    'Financials': 'XLF',
    'Health Care': 'XLV',
    'Materials': 'XLB',
    'Consumer Discretionary': 'XLY',
    'Real Estate': 'XLRE',
    'Consumer Staples': 'XLP',
    'Communication Services': 'XLC',
    'Energy': 'XLE'
}


#Checks data for all sectors

def checkSectors():
    sectorList=[]
    for sName, sID in sectorID.items():
        priceList = get_price(sID) #Recieves some arr ['123.53', '+1.25', '(0.86%)']"
        percent = float(priceList[2][1:-2]) #'(0.86%)' -> 0.86
        if priceList[1][0] != '+':
            percent *= -1  #If price change is negative then change percent too
        sectorList.append((sName, percent))

    finalList = sorted(sectorList, key=lambda x: x[1])

    return(finalList)
    





#Function for user initialization

def insertUser(cursor,userID,username,password):
    sql = "INSERT INTO Users (userID, userName, password, amount, buying_power) VALUES (%s, %s, %s, %s, %s)"
    val = (userID, username, password,0,25000)
    cursor.execute(sql, val)
    mydb.commit()


#Function for stock buy transaction + update posistions

def buyStock(cursor,symbol,userID,shares):
    price = get_price(symbol)
    value = float(price[0])
    total = round((value*shares),2)

    #Get current date and time
    time = datetime.datetime.now()

    #Format it to sql date and time format
    formatTime = time.strftime('%Y-%m-%d %H:%M:%S')

    #Check for existing position in the stock
    cursor.execute("SELECT shares, POS FROM positions WHERE symbol = %s AND userID = %s", (symbol, userID))
    existing_position = cursor.fetchone()

    if existing_position:
        #If there is an existing position update the share count and POS averaged
        existing_shares, existing_pos = existing_position
        new_shares = existing_shares + shares
        #Calculate the new average purchase POS price
        new_pos = ((existing_pos * existing_shares) + (value * shares)) / new_shares
        new_shares = existing_position[0] + shares
        cursor.execute("UPDATE positions SET shares = %s, POS = %s WHERE symbol = %s AND userID = %s", (new_shares, new_pos, symbol, userID))
    else:
        #Insert new position if there isnt a current one
        cursor.execute("INSERT INTO positions (symbol, POS, userID, shares) VALUES (%s, %s, %s, %s)", (symbol, value, userID, shares))
    
    #Add to transactions
    sql = "INSERT INTO transactions (symbol, price, userID, shares, value, sale, datetime) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    val = (symbol, value, userID, shares, total, "BUY", formatTime)
    cursor.execute(sql, val)

    #Update buying power and market value
    sql = "UPDATE Users SET amount = amount + %s, buying_power = buying_power - %s WHERE userID = %s"
    cursor.execute(sql, (total, total, userID))
    
    mydb.commit()









def sellStock(cursor, symbol, userID, shares):
    try:
        #Get current date and time
        time = datetime.datetime.now()

        #Format it to sql standards
        formatTime = time.strftime('%Y-%m-%d %H:%M:%S')

        price = get_price(symbol)
        value = float(price[0])
        total = round((value * shares), 2)
        
        cursor.execute("SELECT shares, POS FROM positions WHERE symbol = %s AND userID = %s", (symbol, userID))
        existing_position = cursor.fetchone()
        
        if existing_position:
            existing_shares, existing_pos = existing_position
            new_shares = existing_shares + shares

            new_pos = ((existing_pos * existing_shares) + (value * shares)) / new_shares
            new_shares = existing_position[0] - shares
            cursor.execute("UPDATE positions SET shares = %s, POS = %s WHERE symbol = %s AND userID = %s", (new_shares, new_pos, symbol, userID))
        else:
            #Insert new position
            cursor.execute("INSERT INTO positions (symbol, POS, userID, shares) VALUES (%s, %s, %s, %s)", (symbol, value, userID, -shares))
        
        
        #Insert transaction
        sql = "INSERT INTO transactions (symbol, price, userID, shares, value, sale, datetime) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (symbol, value, userID, shares, total, "SELL", formatTime)
        cursor.execute(sql, val)
        
        # Update user's amount and buying_power
        sql = "UPDATE Users SET amount = amount - %s, buying_power = buying_power + %s WHERE userID = %s"
        cursor.execute(sql, (total, total, userID))
        
        mydb.commit()


    except mysql.connector.Error as e:
        if e.errno == 1644:  
            messagebox.showerror("Error", "You cannot sell more shares than owned!")
            app.stockCount=0
        else:
            print("Error occurred during sell transaction:", e)
        mydb.rollback()



"""
Examples of manual user insertion
insertUser(mycursor,70900,'user','root')
buyStock(mycursor,'aapl',70900,8)
buyStock(mycursor,'amzn',70900,1)
buyStock(mycursor,'msft',70900,7)
buyStock(mycursor,'tsla',70900,10)
insertUser(mycursor,15861,'userAdmin2','secretPassword')
buyStock(mycursor,'amd',15861,1)
buyStock(mycursor,'dg',15861,7)
buyStock(mycursor,'f',70900,5)
sellStock(mycursor,'aapl',70900,3)
buyStock(mycursor,'aapl',15861,6)
sellStock(mycursor,'aapl',15861,3)
"""

#Function to get total value of user account

def totalValue(cursor,userID):
    sql = "SELECT amount, buying_power FROM users WHERE userID = %s"
    cursor.execute(sql,(userID,))
    items = cursor.fetchall()
    if items:
        total = float(items[0][0]) + float(items[0][1])
        #Returns buying power + current posistions value
        return total
    else:
        print("Invalid userID")
        return None


#Function for checking user PnL stats and updating database information

def profitNLoss(cursor,userID):
    #Chart = posID, symbol, POS, shares, userID
    #Grabs format ROW = (214, 'aapl', 183.38, 8, 70900)
    sql = "SELECT * FROM positions WHERE userID = %s"
    cursor.execute(sql,(userID,))
    items = cursor.fetchall()
    newAccountAmount =0.00

    profitNLoss= []
    total=0
    for row in items:
        symbol = str(row[1])
        POS = float(row[2])
        shares = int(row[3])
        
        priceList = get_price(str(symbol))
        currentPrice = float(priceList[0])
        #Gets current stock price ^ 
        currTotal = (currentPrice*shares) #Current value of shares owned
        newAccountAmount += (currTotal)
    
        #Gets individual stock PnL
        stockPNL = round(currTotal-(POS*shares),2)
        
        #Gets stock percent from POS
        percent_change = round(((currentPrice - POS) / POS) * 100, 2)

        #Format Handling
        if stockPNL >= 0:
            profitNLoss.append(f"{symbol.upper()}:  $+{stockPNL}  ({percent_change}%)")
        else:
            profitNLoss.append(f"{symbol.upper()}:  ${stockPNL}  ({percent_change}%)")
            
        total+=stockPNL

    #Update user markt value
    sql = "UPDATE Users SET amount = %s WHERE userID = %s"
    cursor.execute(sql, (newAccountAmount, userID))
    mydb.commit()

    #Return per-position PnL and Total PnL
    return(profitNLoss,total)



"""
////////////////////////////////////////

Start Of GUI Code:

////////////////////////////////////////
"""



customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("dark-blue")  #Set Default Theme

#Class Initialization for GUI

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        
        #Config window
        self.title("Database Project - Paper Trading")
        self.geometry(f"{1300}x{650}")

        #Config grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=0)



        #Create sidebar frame

        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=8, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="BirdBox", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        

        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=8, column=0, padx=20, pady=25, sticky="s")



        #Create search box and enter button

        self.entry = customtkinter.CTkEntry(self, placeholder_text="Enter a Stock Ticker Symbol")
        self.entry.grid(row=3, column=1, columnspan=2, padx=(20, 0), pady=(20, 20), sticky="nsew")


        self.main_button_1 = customtkinter.CTkButton(master=self, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"),text="Search", command=self.search_button_event)
        self.main_button_1.grid(row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew")


        #Create textbox for stock information

        self.textbox = customtkinter.CTkTextbox(self, width=250,font=customtkinter.CTkFont(size=20, weight="bold"))
        self.textbox.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")



        #Create tabview for sector data and open position PnL

        self.tabview = customtkinter.CTkTabview(self, width=250)
        self.tabview.grid(row=0, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.tabview.add("All Sectors")
        self.tabview.add("Open P&L")
        self.tabview.tab("All Sectors").grid_columnconfigure(0, weight=1) 
        self.tabview.tab("Open P&L").grid_columnconfigure(0, weight=1)

        
        

        #Sector Update Grid

        self.sector_label_all = customtkinter.CTkLabel(self.tabview.tab("All Sectors"), text="Insert sectors here")
        self.sector_label_all.grid(row=0, column=0, padx=20, pady=20)

        #Initialize sector web scraping and set to variable
        Sector_Update = checkSectors()

        #Set label to current sector values
        
        myStr =''
        for i, (sector, percent) in enumerate(Sector_Update):
            if float(percent) >= 0:
                # Make the positive percent sectors green
                if i == 0:
                    myStr += f"{sector}: {percent}%" + "   "
                    self.sector_label_all.configure(text=myStr, font=customtkinter.CTkFont(size=13, weight="bold"))
                else:
                    myStr += f"\n{sector}: {percent}%" + "   "
                    self.sector_label_all.configure(text=myStr, font=customtkinter.CTkFont(size=13, weight="bold"))
            else:
                if i ==0:
                    myStr += f"{sector}: {percent}%" + "   "
                    
                    self.sector_label_all.configure(text=myStr, font=customtkinter.CTkFont(size=13, weight="bold"))
                else:    
                    myStr += f"\n{sector}: {percent}%" + "   "
                    self.sector_label_all.configure(text=myStr, font=customtkinter.CTkFont(size=13, weight="bold"))

        #Use previous variable for text entry of Sector status's
        self.sector_label_all.configure(text=f"{myStr}")

        self.open_PnL_Label = customtkinter.CTkLabel(self.tabview.tab("Open P&L"), text="Login To View Your Open P&L")
        self.open_PnL_Label.grid(row=0, column=0, padx=20, pady=20)


        #Login Buttons Frame
        
        self.login = False
        
        self.login_frame = customtkinter.CTkScrollableFrame(self, label_text= "Login / Sign Up")
        self.login_frame.grid(row=0, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")


        #Login Button

        self.login_prompt_button = customtkinter.CTkButton(master=self.login_frame, text="Click To Login",command=self.login_button_click)
        self.login_prompt_button.grid(row=3, column=2, pady=10,padx=30, sticky="n")
        self.signUp_prompt_button = customtkinter.CTkButton(master=self.login_frame, text="Create An Account",command=self.signUp_button_click)
        self.signUp_prompt_button.grid(row=4, column=2, pady=10,padx=30, sticky="n")



        #Account P&L (Open and Life Time)
        
        self.profit_and_loss_frame = customtkinter.CTkTabview(self)
        self.profit_and_loss_frame.add("Open P&L")
        self.profit_and_loss_frame.add("Life Time Account P&L")
        self.profit_and_loss_frame.tab("Life Time Account P&L").grid_columnconfigure(0, weight=1) 
        self.profit_and_loss_frame.tab("Open P&L").grid_columnconfigure(0, weight=1)

        self.profit_and_loss_frame.grid(row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.profit_and_loss_frame.grid_columnconfigure(0, weight=1)
        self.profit_and_loss_frame.grid_rowconfigure(4, weight=1)

        self.accountPNL_open = customtkinter.CTkLabel(self.profit_and_loss_frame.tab("Open P&L"), text="Login To View Your Account Info")
        self.accountPNL_open.grid(row=0, column=0, padx=20, pady=20)
        self.accountPNL_life = customtkinter.CTkLabel(self.profit_and_loss_frame.tab("Life Time Account P&L"), text="Login To View Your Account Info")
        self.accountPNL_life.grid(row=0, column=0, padx=20, pady=20)
        
        


        #Account Info
        self.scrollable_frame = customtkinter.CTkScrollableFrame(self, label_text="Account Information", width = 50)
        self.scrollable_frame.grid(row=1, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_rowconfigure(0, weight=1)

        self.user_total_label = customtkinter.CTkLabel(master=self.scrollable_frame, text = "Login To View Account Info",font=customtkinter.CTkFont(size=13, weight="bold"))
        self.user_total_label.grid(row=1, column=2, padx=(20, 80), pady=(20, 0), sticky="nsew")

        self.user_position_label = customtkinter.CTkLabel(master=self.scrollable_frame,text = "",font=customtkinter.CTkFont(size=13, weight="bold"))
        self.user_position_label.grid(row=2, column=2, padx=(20, 60), pady=(20, 0), sticky="nsew")

        self.user_buyingP_label = customtkinter.CTkLabel(master=self.scrollable_frame,text = "",font=customtkinter.CTkFont(size=13, weight="bold"))
        self.user_buyingP_label.grid(row=3, column=2, padx=(20, 60), pady=(20, 0), sticky="nsew")


        # Positions Box

        self.position_frame = customtkinter.CTkScrollableFrame(self, label_text = "My Positions")
        self.position_frame.grid(row=1, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.positions_label = customtkinter.CTkLabel(master=self.position_frame, text="Login to View Your Positions",font=customtkinter.CTkFont(size=12, weight="normal"))
        self.positions_label.grid(row=0, column=0, padx=(0,150), pady=20)

        #Default Stock Info status + Default Appearence Mode
        self.appearance_mode_optionemenu.set("Dark")
        self.textbox.insert("0.0", "Stock Info:\n\n" + "Search a stock in the search bar below to find out its information!")

    
        """
        ////////////////////////////////////
        End of Default Window Initialization
        ////////////////////////////////////
        """



    #Function to handle input from the search bar and retrieve stock data
    
    def search_button_event(self): 
        # Retrieve the text entered in the entry widget
        search_text = self.entry.get()
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM Stocks WHERE symbol = %s", (search_text,))
        items = cursor.fetchall()
        
        self.textbox.delete("1.0", "end")
        self.ticker_symbol = search_text
        
        #Use bot to scrape the live stock data
        currPrice = get_price(self.ticker_symbol)
        self.searchPrice = currPrice[0]
        
        if not items:
            #If the stock isnt in the stocks database, still insert symbol and live price
            self.textbox.insert("0.0",f"({self.ticker_symbol.upper()}): Price: ${currPrice[0]}\n\nThis Stock Is Not In The S&P 500.")
            
        else:    
            for row in items:
                #Code for displaying the stock data in the stock information textbox
                self.ticker_symbol = row[0]
                company_name = row[1]
                sector = row[2]
                industry = row[3]
                location = row[4]
                sp500 = row[5]
                cik = row[6]
                founded_year = row[7]
                #Constructing / Formatting the stock explanation
                explanation = f"({self.ticker_symbol.upper()}): Price: ${currPrice[0]}\n\n{company_name}  is a {industry} company in the {sector} sector."
                explanation += f" It was founded in {founded_year} in {location}."
                explanation += f" The Central Index Key for {company_name} is {cik}, It was initially added to the S&P 500 in {sp500}.\n\n"
                
            self.textbox.insert("0.0", explanation)

        #Function is ran if the user is logged in as an account
        if self.login:
            
            #Buy and sell button format
            self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, text="Buy", command=self.buy_button_event, bg_color='transparent', fg_color='green')
            self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
            self.sidebar_button_2 = customtkinter.CTkButton(self.sidebar_frame, text="Sell", command=self.sell_button_event, bg_color='transparent', fg_color='red')
            self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

            # Plus and Minus Button format
            self.button_plus = customtkinter.CTkButton(self.sidebar_frame, text="+", command=self.plus_button_event, bg_color='transparent', fg_color='blue')
            self.button_plus.grid(row=3, column=0, padx=20, pady=15, sticky="ew")
            self.button_minus = customtkinter.CTkButton(self.sidebar_frame, text="-", command=self.minus_button_event, bg_color='transparent', fg_color='grey')
            self.button_minus.grid(row=4, column=0, padx=20, pady=15, sticky="ew")
            self.stockCount = 0
            self.label_number = customtkinter.CTkLabel(self.sidebar_frame, text=f"Shares: {self.stockCount}", font=customtkinter.CTkFont(size=14, weight="bold"))
            self.label_number.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

            #Format for labels under side pannel buttons
            self.MarketValue = 0
            self.value_number = customtkinter.CTkLabel(self.sidebar_frame, text=f"Market Value: ${self.MarketValue}", font=customtkinter.CTkFont(size=14, weight="bold"))
            self.value_number.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

            self.buyingP_left_number = customtkinter.CTkLabel(self.sidebar_frame, text=f"Buying Power: ${round(float(self.buyingP),2)}", font=customtkinter.CTkFont(size=14, weight="bold"))
            self.buyingP_left_number.grid(row=7, column=0, padx=20, pady=0, sticky="ew")
            
        cursor.close()
        
            





    #Function for logging in
    
    def login_button_click(self):
        #Initialize window
        dialog = customtkinter.CTkInputDialog(text="Username:", title="Login Window")
        username = dialog.get_input()
        dialog = customtkinter.CTkInputDialog(text="Password:", title="Login Window")
        password = dialog.get_input()

        #Check database for inputed username and password
        mycursor.execute("SELECT userID FROM users WHERE userName = %s AND password = %s", (username,password))
        id = str(mycursor.fetchone())

        #id is set to none if the user is not in the database
        if id != "None":
            self.user_ID = int(id[1:-2]) #Remove sql formating and convert back to int
            self.login = True #Let the class know that the user is now logged in!
            
            self.login_frame.configure(label_text = f"Welcome {username}")
            self.login_prompt_button.configure(text="Login As Another User")
            #Updating position numbers and all data labels
            self.update_positions()
            
        else:
            #Pop up window if the credentials are invalid / non existent 
            messagebox.showerror("Error", "Invalid Credentials.")
            

    #Function for creating a new user account
    def signUp_button_click(self):
        # Get username and password from user input dialogs
        dialog = customtkinter.CTkInputDialog(text="Create a Username:", title="Sign Up Window")
        username = dialog.get_input()
        dialog = customtkinter.CTkInputDialog(text="Enter a Password:", title="Sign Up Window")
        password = dialog.get_input()
        #Check if username already exists
        mycursor.execute("SELECT * FROM Users WHERE userName = %s", (username,))
        existing_user = mycursor.fetchone()

        #Make sure the username does not already exists
        if existing_user:
            messagebox.showerror("Error", "username already exists.")
            return
        userID = random.randint(10000, 99999)
        insertUser(mycursor,userID,str(username),str(password))

        #Automatically prompt for login after successfull login
        self.login_button_click()
                        

    #Function to update all stock and database data
    def update_positions(self):
        #Recieve per-position PnL and Overall PnL
        positionPnL, total_open_PnL = profitNLoss(mycursor,self.user_ID)

        #Update text for all individual position updates
        text=''
        for item in positionPnL:
            text += f"{item}\n\n"
        self.open_PnL_Label.configure(text = f"{text}")

        #Set label for total account value
        totAccWorth = totalValue(mycursor,self.user_ID)
        totAccWorth = "{:.2f}".format(round(totAccWorth,2))
        self.user_total_label.configure(text = f"Account Value: ${totAccWorth}")

        #Grab updated amount (After running profitNLoss() ) and set to label
        mycursor.execute("SELECT amount from users WHERE userID = %s", (self.user_ID,))
        amount = str(mycursor.fetchone())
        amount = str(amount[1:-2])
        val = round(float(amount),2)
        val = "{:.2f}".format(val)
        self.user_position_label.configure(text = f"Market Value: ${val}")

        #Update buying power as well
        mycursor.execute("SELECT buying_power from users WHERE userID = %s", (self.user_ID,))
        self.buyingP = str(mycursor.fetchone())
        self.buyingP = str(self.buyingP[1:-2])
        val = round(float(self.buyingP),2)
        val = "{:.2f}".format(val)
        self.user_buyingP_label.configure(text = f"Buying Power: ${val}")

        #Format and label updating for acive position information
        sql = ("SELECT * FROM positions WHERE userID = %s")
        mycursor.execute(sql,(self.user_ID,))
        items = mycursor.fetchall()
        
        #Check and see if there are active positions
        if not items:
            self.positions_label.configure(text=f"No Active Positions")
            return
            
        #Format of items[] = (214, 'aapl', 183.38, 8, 70900)
        positions= ''
        
        for row in items:
            symbol = str(row[1])
            unRoundPOS = round(float(row[2]),2)
            POS = "{:.2f}".format(unRoundPOS)
            positions += f"{symbol.upper()}:  {row[3]} Shares @ POS ${POS}\n\n"
            
        #Set for position data share count and updated POS
        self.positions_label.configure(text=f"{positions}")

        #Get life time account PnL and set to label
        acctPNL = round(float(totAccWorth)-25000,2)
        
        if acctPNL>=0:
            acctPNL = "{:.2f}".format(acctPNL)
            self.accountPNL_life.configure(text=f"\n\n Life Time P&L = $+{acctPNL}", text_color="green", font=customtkinter.CTkFont(size=16, weight="bold"))
        else:
            acctPNL = "{:.2f}".format(acctPNL)
            self.accountPNL_life.configure(text=f"\n\n Life Time P&L = ${acctPNL}", text_color="red", font=customtkinter.CTkFont(size=16, weight="bold"))

        #Get current total open PnL and set to label
        if total_open_PnL>=0:
            total_open_PnL = "{:.2f}".format(total_open_PnL)
            self.accountPNL_open.configure(text=f"\n\n Open P&L = $+{total_open_PnL}", text_color="green", font=customtkinter.CTkFont(size=16, weight="bold"))
        else:
            total_open_PnL = "{:.2f}".format(total_open_PnL)
            self.accountPNL_open.configure(text=f"\n\n Open P&L = ${total_open_PnL}", text_color="red", font=customtkinter.CTkFont(size=16, weight="bold"))


    
    #Stock count button plus click handling
    
    def plus_button_event(self):
        #Stock count variable for amount to buy / sell updated
        self.stockCount+=1
        #Grab buying power
        buyingPleft = float(self.buyingP)
        #Buying power left after purchasing given number of stocks
        buyingPleft = round((buyingPleft - (float(self.searchPrice) * self.stockCount)),2)

        #Prevent overbuying
        if buyingPleft < 0:
            self.stockCount-=1
            return #break
        #Format Buying Power Left Label
        buyingPleft = "{:.2f}".format(buyingPleft)
        self.buyingP_left_number.configure(text = f"Buying Power: ${round(float(buyingPleft),2)}")

        self.label_number.configure(text=f"Shares: {self.stockCount}")
        self.button_minus.configure(fg_color="blue")
        
        #Format market value label of searched stock symbol * number of shares being requested (total value)
        marketValue = round((float(self.searchPrice)*self.stockCount),2)
        marketValue = "{:.2f}".format(marketValue)
        self.value_number.configure(text=f"Market Value: ${marketValue}")


    
    #Stock count button minus click handling
    
    def minus_button_event(self):
        #Preventing negative sell count
        if self.stockCount >=1:
            if self.stockCount <= 1:
                self.button_minus.configure(fg_color="grey")
            else:
                self.button_minus.configure(fg_color="blue")

            self.stockCount-=1
            buyingPleft = float(self.buyingP)
            buyingPleft = round((buyingPleft - (float(self.searchPrice) * self.stockCount)),2)    
            if buyingPleft > 0:  
                buyingPleft = "{:.2f}".format(buyingPleft)
                self.buyingP_left_number.configure(text = f"Buying Power: ${buyingPleft}")
            marketValue = round((float(self.searchPrice)*self.stockCount),2)
            self.label_number.configure(text=f"Shares: {self.stockCount}")
            marketValue = "{:.2f}".format(marketValue)
            self.value_number.configure(text=f"Market Value: ${marketValue}")


    #Appearence mode button switch handling
    
    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)


    #Buy button press handling
    
    def buy_button_event(self):
        buyingPleft = float(self.buyingP)
        buyingPleft = (buyingPleft - (float(self.searchPrice) * self.stockCount))
        #Double checking to make sure the user has proper funds if GUI fails
        if buyingPleft > 0:
            buyStock(mycursor,self.ticker_symbol,self.user_ID,self.stockCount)
            #Resetting Values then updating
            self.stockCount = 0
            self.label_number.configure(text=f"Shares: {self.stockCount}")
            self.update_positions()
        else:
            #Error Handling
            messagebox.showerror("Error", "Insufficient Funds.")
        

    #Sell button event handling
    
    def sell_button_event(self):
        sellStock(mycursor,self.ticker_symbol,self.user_ID,self.stockCount)
        self.stockCount = 0
        self.label_number.configure(text=f"Shares: {self.stockCount}")
        #SQL Trigger will prevent overselling of a stock

        #Updating all values
        self.update_positions()
    

#Launch App
if __name__ == "__main__":
    app = App()
    app.mainloop()


"""
///////////////////////////////////////////////

AES Encryption Algorithm For Database Data

///////////////////////////////////////////////
"""
#74 68 65 20 6D 6F 72 65 20 79 6F 75 20 73 65 65
import numpy as np
class AES:
  def __init__(self, key):
    self.key = key
    self.AES_Sbox = (
        0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67,
        0x2B, 0xFE, 0xD7, 0xAB, 0x76, 0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59,
        0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0, 0xB7,
        0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1,
        0x71, 0xD8, 0x31, 0x15, 0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05,
        0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75, 0x09, 0x83,
        0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29,
        0xE3, 0x2F, 0x84, 0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B,
        0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF, 0xD0, 0xEF, 0xAA,
        0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C,
        0x9F, 0xA8, 0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC,
        0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2, 0xCD, 0x0C, 0x13, 0xEC,
        0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19,
        0x73, 0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE,
        0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB, 0xE0, 0x32, 0x3A, 0x0A, 0x49,
        0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
        0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4,
        0xEA, 0x65, 0x7A, 0xAE, 0x08, 0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6,
        0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A, 0x70,
        0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9,
        0x86, 0xC1, 0x1D, 0x9E, 0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E,
        0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF, 0x8C, 0xA1,
        0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0,
        0x54, 0xBB, 0x16)
    self.AES_Sbox_array = np.array(self.AES_Sbox, dtype=np.uint8).reshape((16, 16))
    self.AES_SboxInverse = (
        0x52, 0x09, 0x6A, 0xD5, 0x30, 0x36, 0xA5, 0x38, 0xBF, 0x40, 0xA3, 0x9E,
        0x81, 0xF3, 0xD7, 0xFB, 0x7C, 0xE3, 0x39, 0x82, 0x9B, 0x2F, 0xFF, 0x87,
        0x34, 0x8E, 0x43, 0x44, 0xC4, 0xDE, 0xE9, 0xCB, 0x54, 0x7B, 0x94, 0x32,
        0xA6, 0xC2, 0x23, 0x3D, 0xEE, 0x4C, 0x95, 0x0B, 0x42, 0xFA, 0xC3, 0x4E,
        0x08, 0x2E, 0xA1, 0x66, 0x28, 0xD9, 0x24, 0xB2, 0x76, 0x5B, 0xA2, 0x49,
        0x6D, 0x8B, 0xD1, 0x25, 0x72, 0xF8, 0xF6, 0x64, 0x86, 0x68, 0x98, 0x16,
        0xD4, 0xA4, 0x5C, 0xCC, 0x5D, 0x65, 0xB6, 0x92, 0x6C, 0x70, 0x48, 0x50,
        0xFD, 0xED, 0xB9, 0xDA, 0x5E, 0x15, 0x46, 0x57, 0xA7, 0x8D, 0x9D, 0x84,
        0x90, 0xD8, 0xAB, 0x00, 0x8C, 0xBC, 0xD3, 0x0A, 0xF7, 0xE4, 0x58, 0x05,
        0xB8, 0xB3, 0x45, 0x06, 0xD0, 0x2C, 0x1E, 0x8F, 0xCA, 0x3F, 0x0F, 0x02,
        0xC1, 0xAF, 0xBD, 0x03, 0x01, 0x13, 0x8A, 0x6B, 0x3A, 0x91, 0x11, 0x41,
        0x4F, 0x67, 0xDC, 0xEA, 0x97, 0xF2, 0xCF, 0xCE, 0xF0, 0xB4, 0xE6, 0x73,
        0x96, 0xAC, 0x74, 0x22, 0xE7, 0xAD, 0x35, 0x85, 0xE2, 0xF9, 0x37, 0xE8,
        0x1C, 0x75, 0xDF, 0x6E, 0x47, 0xF1, 0x1A, 0x71, 0x1D, 0x29, 0xC5, 0x89,
        0x6F, 0xB7, 0x62, 0x0E, 0xAA, 0x18, 0xBE, 0x1B, 0xFC, 0x56, 0x3E, 0x4B,
        0xC6, 0xD2, 0x79, 0x20, 0x9A, 0xDB, 0xC0, 0xFE, 0x78, 0xCD, 0x5A, 0xF4,
        0x1F, 0xDD, 0xA8, 0x33, 0x88, 0x07, 0xC7, 0x31, 0xB1, 0x12, 0x10, 0x59,
        0x27, 0x80, 0xEC, 0x5F, 0x60, 0x51, 0x7F, 0xA9, 0x19, 0xB5, 0x4A, 0x0D,
        0x2D, 0xE5, 0x7A, 0x9F, 0x93, 0xC9, 0x9C, 0xEF, 0xA0, 0xE0, 0x3B, 0x4D,
        0xAE, 0x2A, 0xF5, 0xB0, 0xC8, 0xEB, 0xBB, 0x3C, 0x83, 0x53, 0x99, 0x61,
        0x17, 0x2B, 0x04, 0x7E, 0xBA, 0x77, 0xD6, 0x26, 0xE1, 0x69, 0x14, 0x63,
        0x55, 0x21, 0x0C, 0x7D)
    self.AES_SboxInverse_array = np.array(self.AES_SboxInverse, dtype=np.uint8).reshape(
      (16, 16))
    self.AES_Encrypt()
  

  #Xors two binary string
  def xor(self, byte1, byte2):
    result = []
    for bit1, bit2 in zip(byte1, byte2):
      if bit1 == bit2:
        result.append("0")
      else:
        result.append("1")
    #print(byte1 + "   " + byte2+"  =  "+str(result))
    return ''.join(result)
  
  
  
  
  
  #Char to binary
  def toBinary(self, a):
    binary_list = []
    for char in a:
      binary_char = format(ord(char), '08b')
      binary_list.append(binary_char)
    return binary_list
  
  
  #Hex to binary
  def hex_to_binary(self, hex_string):
    decimal_number = int(hex_string, 16)
    binary_string = bin(decimal_number)[2:].zfill(8)
    return (binary_string)
  
  
  def addRoundKey(self, state, keyBytesArr):
    for col in range(4):
      for row in range(4):
        temp = self.xor(state[col, row], keyBytesArr[col, row])
        self.state[col, row] = temp
  
  #given input byte in binary switch and return as uint8
  def SBox_Lookup(self, byte):
    b11 = byte[:4]
    b12 = byte[4:]
    column = int(b11, 2)
    row = int(b12, 2)
    return (self.AES_Sbox_array[column, row])
  

  def substituteArray(self, state):
    for col in range(4):
      for row in range(4):
        self.state[col, row] = (self.SBox_Lookup(state[col, row]))
  
  
  def shiftRows(self, state):
    state[:, 1] = [state[1, 1], state[2, 1], state[3, 1], state[0, 1]]
    # Shift the third column two positions down
    state[:, 2] = [state[2, 2], state[3, 2], state[0, 2], state[1, 2]]
    # Shift the fourth column three positions down
    state[:, 3] = [state[3, 3], state[0, 3], state[1, 3], state[2, 3]]
    return state
  




  

  def gmul(self, a, b):
    if b == 1:
        return a
    tmp = (a << 1) & 0xff
    if b == 2:
        return tmp if a < 128 else tmp ^ 0x1b
    if b == 3:
        return self.gmul(a, 2) ^ a
    
  def mixSingleColumn(self, col):
    a=int(col[0])
    b=int(col[1])
    c=int(col[2])
    d=int(col[3])
    col[0] = (self.gmul(a, 2) ^ self.gmul(b, 3) ^ self.gmul(c, 1) ^ self.gmul(d, 1))
    col[1] = (self.gmul(a, 1) ^ self.gmul(b, 2) ^ self.gmul(c, 3) ^ self.gmul(d, 1))
    col[2] = (self.gmul(a, 1) ^ self.gmul(b, 1) ^ self.gmul(c, 2) ^ self.gmul(d, 3))
    col[3] = (self.gmul(a, 3) ^ self.gmul(b, 1) ^ self.gmul(c, 1) ^ self.gmul(d, 2))
    return col

  def mixColumns(self, state):
      # Create an empty array to store the result
        result = np.empty_like(state, dtype=np.uint8)
        
        # Apply mixSingleColumn operation to each column separately
        for col_idx in range(4):
            column = state[col_idx,:]  # Extract the column
            mixed_column = self.mixSingleColumn(column)  # Apply mixSingleColumn function
            result[:, col_idx] = mixed_column  # Store the result back into the result array
        
        return(result)




    


    
  
  def AES_Encrypt(self):
    #Read file
    rounds=1
    input = "input.txt"
    with open(input, "r") as file:
      #Read first 16 chars
      data = self.toBinary(file.read()[:16])
  
    # Grab first 128 bits of the ciphertext and the entire key and condense to a 4x4 array of bytes for both
    self.state = np.array(list(data)).reshape(4, 4).T
    self.keyBytes = [key[i:i + 8] for i in range(0, len(key), 8)]
    self.keyBytesArr = np.array(self.keyBytes).reshape(4, 4)

    while rounds <=10:
      print("\nStarting text for round "+str(rounds)+":")
      for row in range(4):
        print(self.state[0, row] + " " + self.state[1, row] + " " + self.state[2, row] + " " +
              self.state[3, row] + " ")
      print("\n")

      print("\nKey "+str(rounds)+" in Binary:")
      for row in range(4):
        print(self.keyBytesArr[0, row] + " " + self.keyBytesArr[1, row] + " " +
              self.keyBytesArr[2, row] + " " + self.keyBytesArr[3, row] + " ")
        
        
      #RoundKey
      self.addRoundKey(self.state, self.keyBytesArr)
      print("\nCiphertext After Round Key:")
      for row in range(4):
        print(self.state[0, row] + " " + self.state[1, row] + " " + self.state[2, row] + " " +
              self.state[3, row] + " ")
      print("\n")
    
      #Substiute
      self.substituteArray(self.state)
      print("\nCiphertext After Substitution:")
      for row in range(4):
        print(self.state[0, row] + " " + self.state[1, row] + " " + self.state[2, row] + " " +
              self.state[3, row] + " ")
      print("\n")
    
      #Shift Rows
      self.state = self.shiftRows(self.state)
      print("\nCiphertext After Shift Rows: (INTEGER)")
      for row in range(4):
        print(self.state[0, row] + " " + self.state[1, row] + " " + self.state[2, row] + " " +
              self.state[3, row] + " ")



      #Shift Mix Columns
      self.state = (self.mixColumns(self.state))
      print("\nCiphertext After Mix Columns: (HEX)")
      
      for row in range(4):
        print(hex(self.state[0, row])[2:].zfill(2) + " " +
                hex(self.state[1, row])[2:].zfill(2) + " " +
                hex(self.state[2, row])[2:].zfill(2) + " " +
                hex(self.state[3, row])[2:].zfill(2))
        

      binary_string = ''.join([format(num, '08b') for num in self.state.flatten()])
      self.bin = [binary_string[i:i + 8] for i in range(0, len(binary_string), 8)]
      self.state = np.array(self.bin).reshape(4, 4)

      print("\n")
      rounds+=1
    print("\n\nFINAL OUTPUT AFTER 10 ROUNDS:\n")
    result = ""
    for row in range(4):
        # Print in order left to right
        result += ''.join(hex(self.state[row, 0]),
                          hex(self.state[row, 1]),
                          hex(self.state[row, 2]),
                          hex(self.state[row, 3]))
    print(result)
